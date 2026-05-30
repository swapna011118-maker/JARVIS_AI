import asyncio
from PIL import Image
from time import sleep
import os
import httpx
from urllib.parse import quote

def open_images(prompt):
    folder_path = "Data"
    safe_prompt = prompt.replace(" ", "_")
    image_count = 0

    for i in range(1, 3):
        image_path = os.path.join(folder_path, f"{safe_prompt}{i}.jpg")
        if os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                img.show()
                image_count += 1
                sleep(0.5)
            except IOError:
                pass

    if image_count > 0:
        print(f"✓ Opened {image_count} image(s)")

async def generate_single_image(prompt: str, index: int):
    try:
        enhanced_prompt = f"{prompt}, ultra detailed, 8k, photorealistic, masterpiece, high resolution"
        url = f"https://image.pollinations.ai/prompt/{quote(enhanced_prompt)}"

        headers = {"User-Agent": "Mozilla/5.0"}

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            if response.status_code == 200:
                print(f"  ✓ Image {index} generated")
                return response.content
            else:
                print(f"  ✗ Image {index} failed (HTTP {response.status_code})")
                return None

    except asyncio.TimeoutError:
        print(f"  ✗ Image {index} timed out")
        return None
    except Exception as e:
        print(f"  ✗ Image {index} error: {str(e)[:60]}")
        return None

async def generate_images(prompt: str):
    print(f"\n🎨 Generating images for: '{prompt}'")

    # Generate 2 at a time with a small gap between requests
    task1 = asyncio.create_task(generate_single_image(prompt, 1))
    await asyncio.sleep(2)  # small delay to avoid simultaneous hits
    task2 = asyncio.create_task(generate_single_image(prompt, 2))

    images = await asyncio.gather(task1, task2)

    os.makedirs("Data", exist_ok=True)
    success_count = 0
    safe_prompt = prompt.replace(" ", "_")

    for i, image_data in enumerate(images, 1):
        if image_data:
            try:
                filepath = f"Data/{safe_prompt}{i}.jpg"
                with open(filepath, 'wb') as f:
                    f.write(image_data)
                success_count += 1
            except Exception:
                pass

    print(f"✓ Done: {success_count}/2 saved\n")
    return success_count > 0

def GenerateImages(prompt):
    try:
        success = asyncio.run(generate_images(prompt))
        if success:
            sleep(2)
            open_images(prompt)
        return success
    except Exception:
        return False

def ensure_file_exists():
    os.makedirs("Frontend/Files", exist_ok=True)
    if not os.path.exists("Frontend/Files/ImageGeneration.data"):
        with open("Frontend/Files/ImageGeneration.data", "w") as f:
            f.write("False,False")

def main():
    ensure_file_exists()

    while True:
        try:
            filepath = "Frontend/Files/ImageGeneration.data"

            if not os.path.exists(filepath):
                sleep(2)
                continue

            with open(filepath, "r") as f:
                data = f.read().strip()

            if "," not in data:
                sleep(2)
                continue

            prompt, status = [x.strip() for x in data.split(",")]

            if status == "True" and prompt:
                GenerateImages(prompt)

                with open(filepath, "w") as f:
                    f.write("False,False")
                break
            else:
                sleep(1)

        except Exception:
            sleep(2)

if __name__ == "__main__":
    main()