import os
import requests
import base64
import io
from typing import Dict
from PIL import Image
from llm_pipeline.llm_client import chat


SD_API_URL = "http://127.0.0.1:7860"
DEFAULT_OUTPUT_DIR = "image_tool/image_output"

STYLE_PROMPT = "moody lighting, masterpiece, closeup, focus on face"
NEGATIVE_PROMPT = (
    "text, watermark, bad anatomy, blurry, cartoon, 3d render, disfigured, "
    "low quality, ugly, extra limbs, modern clothing"
)


def _get_visual_prompt_from_llm(char: Dict) -> str:
    """Build a concise visual prompt from a character description."""
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
    Use existing PNG in output_dir if present.
    If missing, try to generate via Automatic1111.
    Returns a relative path or None on total failure.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    safe_name = character["name"].replace(" ", "_")
    filename = f"{safe_name}.png"
    file_path = os.path.join(output_dir, filename)

    # 0. If image already exists, just use it
    if os.path.exists(file_path):
        print(f"   Using existing image for {character['name']}: {file_path}")
        # return a path your templates can use; adjust if needed
        return file_path

    # 1. Get optimized prompt from LLM
    print(f"   optimizing prompt for {character['name']}...")
    visual_keywords = _get_visual_prompt_from_llm(character)
    full_prompt = f"{visual_keywords}, {STYLE_PROMPT}"

    payload = {
        "prompt": full_prompt,
        "negative_prompt": NEGATIVE_PROMPT,
        "steps": 25,
        "cfg_scale": 7,
        "width": 512,
        "height": 768,
        "sampler_name": "Euler a",
    }

    try:
        response = requests.post(url=f"{SD_API_URL}/sdapi/v1/txt2img", json=payload)

        if response.status_code == 200:
            r = response.json()
            image = Image.open(io.BytesIO(base64.b64decode(r["images"][0])))
            image.save(file_path)
            print(f"   Saved: {file_path}")
            return file_path
        else:
            print(f"   API Error {response.status_code}")
            return None

    except requests.exceptions.ConnectionError:
        print("   Error: Automatic1111 API not reachable. (Is it running with --api?)")
        return None
