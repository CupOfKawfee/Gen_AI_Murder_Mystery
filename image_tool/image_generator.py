import os
import requests
import base64
import io
from typing import Dict
from PIL import Image
from llm_pipeline.llm_client import chat

# Automatic1111 Stable Diffusion API URL
SD_API_URL = os.getenv("SD_API_URL", "http://127.0.0.1:7860")
DEFAULT_OUTPUT_DIR = "image_tool/image_output"

# The LoRA (Must match filename in models/Lora without extension) https://huggingface.co/ntc-ai/SDXL-LoRA-slider.nice-hands
HAND_LORA_FILENAME = "SDXL-LoRA-slider.nice-hands" 

# Resolution
IMG_WIDTH = 512
IMG_HEIGHT = 786

# Style Prompts
STYLE_PROMPT = "moody lighting, masterpiece, closeup, focus on face, sharp focus, 8k, detailed skin texture"
NEGATIVE_PROMPT = "text, watermark, bad anatomy, blurry, cartoon, 3d render, disfigured, low quality, ugly, extra limbs, modern clothing"

def _get_visual_prompt_from_llm(char: Dict) -> str:
    """
    Use LLM to convert character description into a concise visual prompt.
    """
    system_prompt = (
        "You are an expert AI art prompter for Stable Diffusion XL. "
        "Convert the character description into a concise list of visual keywords.\n"
        "1. Start with: 'Portrait of a [Age] year old [Gender] [Occupation]...'\n"
        "2. Focus on lighting and textures (e.g. 'soft studio lighting', 'worn leather').\n"
        "3. Output ONLY the raw prompt string. No markdown."
    )
    user_content = (
        f"Name: {char.get('name')}\n"
        f"Occupation: {char.get('occupation')}\n"
        f"Appearance: {char.get('appearance')}\n"
        f"Background: {char.get('background')}\n\n"
        "Create the visual prompt:"
    )
    raw_response = chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
    )
    return raw_response.replace("Prompt:", "").replace('"', "").strip()


def generate_character_image(
    character: Dict, output_dir: str = DEFAULT_OUTPUT_DIR
) -> str | None:
    """
    Generates an image for the given character using Stable Diffusion XL via Automatic1111 API.
    1. Checks if an image already exists for the character in output_dir. If so, returns the path.
    2. Uses LLM to create a visual prompt based on character details.
    3. Configures ADetailer to enhance hand details in the generated image with an lora for good hands.
    4. Sends a request to the Automatic1111 API to generate the image.
    5. Saves and returns the path to the generated image, or None on failure.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    safe_name = character["name"].replace(" ", "_")
    filename = f"{safe_name}.png"
    file_path = os.path.join(output_dir, filename)

    if os.path.exists(file_path):
        print(f"   Using existing image: {file_path}")
        return file_path

    # Generating Main Prompt
    print(f"   Optimizing prompt for {character['name']}...")
    visual_keywords = _get_visual_prompt_from_llm(character)
    main_prompt = f"{visual_keywords}, {STYLE_PROMPT}"

    # Configuring ADetailer for Hands
    adetailer_prompt = f"detailed hands, nice hands, sharp focus, 8k, detailed skin texture, <lora:{HAND_LORA_FILENAME}:2.5>"
    
    adetailer_args = [
        True,   # 1. Enable ADetailer
        False,  # 2. Do not skip img2img
        { 
            "ad_model": "hand_yolov8n.pt",   
            "ad_prompt": adetailer_prompt,
            "ad_negative_prompt": "mutated, extra fingers, missing fingers, disfigured, low quality, ugly, extra limbs",
            "ad_confidence": 0.3,
            "ad_mask_blur": 35,
            "ad_denoising_strength": 0.4,
        }
    ]

    payload = {
        "prompt": main_prompt,
        "negative_prompt": NEGATIVE_PROMPT,
        "steps": 25,
        "cfg_scale": 7,
        "width": IMG_WIDTH,
        "height": IMG_HEIGHT,
        "sampler_name": "DPM++ 2M Karras",
        "restore_faces": False,
        "alwayson_scripts": {
            "ADetailer": {
                "args": adetailer_args
            }
        }
    }

    print(f"   Sending to Automatic1111...")
    
    try:
        response = requests.post(url=f"{SD_API_URL}/sdapi/v1/txt2img", json=payload)
        if response.status_code == 200:
            r = response.json()
            image = Image.open(io.BytesIO(base64.b64decode(r["images"][0])))
            image.save(file_path)
            print(f"   Saved: {file_path}")
            return file_path
        else:
            print(f"   API Error {response.status_code}: {response.text}")
            return None

    except requests.exceptions.ConnectionError:
        print("   Error: Automatic1111 API not reachable.")
        return None
