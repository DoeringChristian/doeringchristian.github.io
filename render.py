from jinja2 import Environment, FileSystemLoader
from omegaconf import OmegaConf
import subprocess
import os
from PIL import Image, ImageOps

ASSETS_DIR = "assets"
LOW_RES_BASE_DIR = os.path.join(ASSETS_DIR, "low_res")
os.makedirs(LOW_RES_BASE_DIR, exist_ok=True)

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".svg")


def process_image_for_low_res(original_path):
    if not original_path.startswith(ASSETS_DIR):
        return original_path  # Not an asset we manage

    # Construct low-res path, preserving directory structure
    relative_path = os.path.relpath(original_path, ASSETS_DIR)
    low_res_path = os.path.join(LOW_RES_BASE_DIR, relative_path)
    os.makedirs(os.path.dirname(low_res_path), exist_ok=True)

    if not os.path.exists(low_res_path):
        try:
            with Image.open(original_path) as img:
                # Apply EXIF orientation first to fix rotated/flipped images
                img = ImageOps.exif_transpose(img)

                # Resize to 400px width, maintaining aspect ratio
                width, height = img.size
                new_width = 400
                new_height = int(new_width * height / width)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                img.save(low_res_path)
                print(f"Generated low-res image: {low_res_path}")
        except Exception as e:
            print(f"Error processing image {original_path}: {e}")
    return low_res_path


IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".svg")


def traverse_and_process_data(item):
    if isinstance(item, dict):
        for key, value in item.items():
            item[key] = traverse_and_process_data(value)
        return item
    elif isinstance(item, list):
        return [traverse_and_process_data(elem) for elem in item]
    elif (
        isinstance(item, str)
        and item.startswith(ASSETS_DIR)
        and item.lower().endswith(IMAGE_EXTENSIONS)
    ):
        low_res_src = process_image_for_low_res(item)
        return {"original_src": item, "low_res_src": low_res_src}
    else:
        return item


# Load data from YAML file using OmegaConf
conf = OmegaConf.load("data.yaml")
# Resolve interpolations
data = OmegaConf.to_container(conf, resolve=True)

# Apply recursive processing to all image paths in data
data = traverse_and_process_data(data)

print(f"Rendering with name: {data['name']}")  # User requested to keep this line

# Set up Jinja2 environment
env = Environment(loader=FileSystemLoader("templates"))

# Render index.html
template = env.get_template("index.html")
output = template.render(data=data)
with open("index.html", "w") as f:
    f.write(output)

print("Successfully rendered templates.")

# Run prettier to format the generated HTML files
try:
    subprocess.run(
        [
            "npm",
            "exec",
            "--yes",
            "--",
            "prettier",
            "--write",
            "index.html",
        ],
        check=True,
    )
    print("Successfully formatted HTML files with Prettier.")
except subprocess.CalledProcessError as e:
    print(f"Error formatting HTML files with Prettier: {e}")
except FileNotFoundError:
    print("Prettier (npx) not found. Please ensure Node.js and Prettier are installed.")
