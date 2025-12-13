import os
import requests
import base64
import io
from typing import Dict
from PIL import Image
from llm_pipeline.llm_client import chat

# ================= CONFIGURATION =================
# Ensure Automatic1111 is running with: ./webui-user.bat --api
SD_API_URL = "http://127.0.0.1:7860"
DEFAULT_OUTPUT_DIR = "character_portraits"

# Global style token to ensure visual consistency
STYLE_PROMPT = "moody lighting, masterpiece, closeup, focus on face"
NEGATIVE_PROMPT = "text, watermark, bad anatomy, blurry, cartoon, 3d render, disfigured, low quality, ugly, extra limbs, modern clothing"

def _get_visual_prompt_from_llm(char: Dict) -> str:
    """
    Uses the local LLM to convert narrative text into a comma-separated visual prompt.
    """
    system_prompt = (
        "You are an expert AI art prompter for Stable Diffusion. "
        "Convert the character description into a concise list of visual keywords.\n"
        "1. Start with: 'Portrait of a [Age] year old [Gender] [Occupation]...'\n"
        "2. Infer age/clothing from 'occupation' and 'background' if not specified.\n"
        "3. Output ONLY the raw prompt string. No markdown."
    )

    user_content = (
        f"Name: {char.get('name')}\n"
        f"Occupation: {char.get('occupation')}\n"
        f"Appearance: {char.get('appearance')}\n"
        f"Background: {char.get('background')}\n\n"
        "Create the visual prompt:"
    )

    # Use your existing chat function
    raw_response = chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        temperature=0.7
    )
    
    # Clean output
    return raw_response.replace("Prompt:", "").replace('"', '').strip()

def generate_character_image(character: Dict, output_dir: str = "image_tool/image_output") -> str:
    """
    Generates an image for a single character and returns the file path.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    safe_name = character['name'].replace(" ", "_")
    filename = f"{safe_name}.png"
    file_path = os.path.join(output_dir, filename)

    # 1. Get Optimized Prompt from LLM
    print(f"   🎨 optimizing prompt for {character['name']}...")
    visual_keywords = _get_visual_prompt_from_llm(character)
    
    full_prompt = f"{visual_keywords}, {STYLE_PROMPT}"
    
    # 2. Payload for Automatic1111
    payload = {
        "prompt": full_prompt,
        "negative_prompt": NEGATIVE_PROMPT,
        "steps": 25,
        "cfg_scale": 7,
        "width": 512,
        "height": 768, # Portrait ratio
        "sampler_name": "Euler a"
    }

    # 3. Call API
    try:
        response = requests.post(url=f'{SD_API_URL}/sdapi/v1/txt2img', json=payload)
        
        if response.status_code == 200:
            r = response.json()
            image = Image.open(io.BytesIO(base64.b64decode(r['images'][0])))
            image.save(file_path)
            print(f"   ✅ Saved: {file_path}")
            return file_path
        else:
            print(f"   ❌ API Error {response.status_code}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Error: Automatic1111 API not reachable. (Is it running with --api?)")
        return None