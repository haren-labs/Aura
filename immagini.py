"""Generazione di immagini con ComfyUI (Stable Diffusion 1.5 con hires fix)."""
import time
import uuid
import base64
import requests
from config import COMFYUI_URL, COMFY_CHECKPOINT, HIRES_BASE, HIRES_SCALE, HIRES_DENOISE
from stato import stato

def genera_immagine(prompt_en):
    """Genera un'immagine con ComfyUI e restituisce base64."""
    try:
        print(f"Generazione immagine: {prompt_en}")
        stato["stato"] = "genero immagine"
        seed = int(time.time()) % 999999999
        # HIRES FIX: base 512x512 -> upscale latent x1.5 (768x768) -> secondo passaggio di raffinamento
        workflow = {
            "1": {"class_type": "KSampler", "inputs": {
                "cfg": 7.5, "denoise": 1,
                "latent_image": ["5", 0], "model": ["4", 0],
                "negative": ["7", 0], "positive": ["6", 0],
                "sampler_name": "dpmpp_2m", "scheduler": "karras",
                "seed": seed, "steps": 25
            }},
            "4": {"class_type": "CheckpointLoaderSimple", "inputs": {
                "ckpt_name": COMFY_CHECKPOINT
            }},
            "5": {"class_type": "EmptyLatentImage", "inputs": {
                "batch_size": 1, "height": HIRES_BASE, "width": HIRES_BASE
            }},
            "10": {"class_type": "LatentUpscaleBy", "inputs": {
                "samples": ["1", 0], "upscale_method": "bislerp",
                "scale_by": HIRES_SCALE
            }},
            "11": {"class_type": "KSampler", "inputs": {
                "cfg": 7.0, "denoise": HIRES_DENOISE,
                "latent_image": ["10", 0], "model": ["4", 0],
                "negative": ["7", 0], "positive": ["6", 0],
                "sampler_name": "dpmpp_2m", "scheduler": "karras",
                "seed": seed, "steps": 18
            }},
            "6": {"class_type": "CLIPTextEncode", "inputs": {
                "clip": ["4", 1],
                "text": f"best quality, highly detailed, {prompt_en}"
            }},
            "7": {"class_type": "CLIPTextEncode", "inputs": {
                "clip": ["4", 1],
                "text": "blurry, bad quality, deformed, ugly, lowres, bad anatomy, watermark, text, signature"
            }},
            "8": {"class_type": "VAEDecode", "inputs": {
                "samples": ["11", 0], "vae": ["4", 2]
            }},
            "9": {"class_type": "SaveImage", "inputs": {
                "filename_prefix": "Aura", "images": ["8", 0]
            }}
        }
        client_id = str(uuid.uuid4())
        response = requests.post(f"{COMFYUI_URL}/prompt", json={
            "prompt": workflow,
            "client_id": client_id
        })
        if response.status_code != 200:
            print(f"Errore ComfyUI: {response.status_code}")
            return None
        prompt_id = response.json().get("prompt_id")
        print(f"Prompt ID: {prompt_id} — aspetto risultato...")
        for _ in range(90):
            time.sleep(2)
            history = requests.get(f"{COMFYUI_URL}/history/{prompt_id}").json()
            if prompt_id in history:
                outputs = history[prompt_id].get("outputs", {})
                for node_id, node_output in outputs.items():
                    if "images" in node_output:
                        img = node_output["images"][0]
                        img_url = f"{COMFYUI_URL}/view?filename={img['filename']}&subfolder={img.get('subfolder','')}&type={img.get('type','output')}"
                        img_response = requests.get(img_url)
                        img_b64 = base64.b64encode(img_response.content).decode('utf-8')
                        stato["ultima_immagine_nome"] = img["filename"]
                        print("Immagine generata!")
                        return img_b64
        print("Timeout generazione immagine")
        return None
    except Exception as e:
        print(f"Errore generazione immagine: {e}")
        return None
