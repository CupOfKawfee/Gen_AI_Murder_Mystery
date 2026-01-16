import os
import json
import requests
import base64
import io
from PIL import Image

# Import the updated client
from llm_pipeline.llm_client import chat_with_tools

# --- Configuration ---
SD_API_URL = os.getenv("SD_API_URL", "http://127.0.0.1:7860")
DEFAULT_OUTPUT_DIR = "image_tool/image_output"
HAND_LORA_FILENAME = "SDXL-LoRA-slider.nice-hands"

# --- 1. The "Inner" Function (The Tool Logic) ---
def _raw_generate_image_api(prompt: str, negative_prompt: str, filename_prefix: str) -> str:
    """
    The actual worker function that hits the Automatic1111 API.
    The LLM does NOT see the code inside here, only the inputs/outputs.
    """
    print(f"   [Tool Executing] Generating image for: '{filename_prefix}'...")
    
    # Ensure directory exists
    if not os.path.exists(DEFAULT_OUTPUT_DIR):
        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)

    safe_name = filename_prefix.replace(" ", "_")
    file_path = os.path.join(DEFAULT_OUTPUT_DIR, f"{safe_name}.png")

    # ADetailer Configuration (Hardcoded logic usually stays here)
    adetailer_args = [
        True, False,
        {
            "ad_model": "hand_yolov8n.pt",
            "ad_prompt": f"detailed hands, <lora:{HAND_LORA_FILENAME}:2.5>",
            "ad_confidence": 0.3,
            "ad_mask_blur": 35,
            "ad_denoising_strength": 0.4,
        }
    ]

    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": 25,
        "width": 512, 
        "height": 768,
        "sampler_name": "DPM++ 2M Karras",
        "alwayson_scripts": {"ADetailer": {"args": adetailer_args}}
    }

    try:
        response = requests.post(url=f"{SD_API_URL}/sdapi/v1/txt2img", json=payload)
        if response.status_code == 200:
            r = response.json()
            image = Image.open(io.BytesIO(base64.b64decode(r["images"][0])))
            image.save(file_path)
            print(f"   [Tool Success] Saved to {file_path}")
            return file_path
        else:
            return f"Error: API Status {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

# --- 2. The Tool Definition (Schema) ---
# This describes the function above to the LLM
IMAGE_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "generate_image_via_api",
        "description": "Generates an image using Stable Diffusion. Use this whenever the user wants to visualize a character or scene.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The highly detailed visual prompt. Include lighting, style (e.g. 'masterpiece, 8k, moody lighting'), and subject details."
                },
                "negative_prompt": {
                    "type": "string",
                    "description": "What to avoid (e.g. 'ugly, blurry, bad anatomy')."
                },
                "filename_prefix": {
                    "type": "string",
                    "description": "A short, safe filename for the image based on the character name."
                }
            },
            "required": ["prompt", "negative_prompt", "filename_prefix"]
        }
    }
}

# --- 3. The "Outer" Function (The Agent Interface) ---
def generate_character_image(character_data: dict) -> str:
    """
    The main entry point. It constructs the context and lets the LLM decide 
    how to call the image generation tool.
    """
    
    # 1. Setup the Agent's Persona
    system_prompt = (
        "You are an expert AI Art Director. Your goal is to generate the perfect prompt "
        "for a Stable Diffusion model based on the character description provided.\n"
        "1. Analyze the character details.\n"
        "2. Construct a 'masterpiece' style prompt with lighting and texture keywords.\n"
        "3. CALL the 'generate_image_via_api' tool with your constructed prompt.\n"
        "4. Do NOT output markdown text, just call the tool."
    )

    user_content = (
        f"Create an image for this character:\n"
        f"Name: {character_data.get('name')}\n"
        f"Role: {character_data.get('occupation')}\n"
        f"Appearance: {character_data.get('appearance')}\n"
        f"Background: {character_data.get('background')}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]

    print(f"--- Agent thinking about {character_data.get('name')} ---")

    # 2. Call the LLM with the Tool Definition
    response_message = chat_with_tools(
        messages=messages,
        tools=[IMAGE_TOOL_DEF],
        tool_choice="auto" # Let LLM decide whether to generate text or call the tool
    )

    # 3. Handle the Tool Call
    if response_message and response_message.tool_calls:
        # The LLM wants to execute a tool
        for tool_call in response_message.tool_calls:
            if tool_call.function.name == "generate_image_via_api":
                
                # Parse arguments generated by the LLM
                args = json.loads(tool_call.function.arguments)
                
                print(f"   [Agent Decision] Calling API with prompt: {args['prompt'][:50]}...")
                
                # Execute the Inner Function
                result_path = _raw_generate_image_api(
                    prompt=args["prompt"],
                    negative_prompt=args.get("negative_prompt", "ugly, blurry"),
                    filename_prefix=args["filename_prefix"]
                )
                
                return result_path
    
    # Fallback if LLM refused to call tool
    return "Error: Agent did not trigger image generation."

# --- Usage Example ---
if __name__ == "__main__":
    char = {
        "name": "Kael",
        "occupation": "Space Marine",
        "appearance": "weary face, scar on cheek, heavy futuristic armor, rain dripping",
        "background": "cyberpunk alleyway neon lights"
    }
    path = generate_character_image(char)
    print(f"Final Result: {path}")