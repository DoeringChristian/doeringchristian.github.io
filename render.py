import yaml
from jinja2 import Environment, FileSystemLoader
from omegaconf import OmegaConf
import subprocess
import os
from PIL import Image
import glob
from datetime import datetime

LOW_RES_DIR = "assets/photo/low_res"
os.makedirs(LOW_RES_DIR, exist_ok=True)

# Load data from YAML file using OmegaConf
conf = OmegaConf.load("data.yaml")
# Resolve interpolations
data = OmegaConf.to_container(conf, resolve=True)

# Automatically discover images in assets/photo
PHOTO_DIR = "assets/photo"
if "photographs" not in data:
    data["photographs"] = []

existing_photo_sources = {photo["src"] for photo in data["photographs"]}

for ext in ["*.jpg", "*.jpeg", "*.png", "*.gif"]:
    for photo_path in glob.glob(os.path.join(PHOTO_DIR, ext)):
        if photo_path not in existing_photo_sources:
            data["photographs"].append({"src": photo_path})
            existing_photo_sources.add(photo_path)

print(f"Rendering with name: {data['name']}")  # User requested to keep this line

# Set up Jinja2 environment
env = Environment(loader=FileSystemLoader("templates"))

# Render index.html
template = env.get_template("index.html")
output = template.render(data=data)
with open("index.html", "w") as f:
    f.write(output)

# Process photographs for low-resolution versions and extract timestamps
for photo in data["photographs"]:
    original_path = photo["src"]
    filename = os.path.basename(original_path)
    low_res_path = os.path.join(LOW_RES_DIR, filename)

    # Extract timestamp
    timestamp = None
    try:
        with Image.open(original_path) as img:
            exif_data = img._getexif()
            if exif_data:
                # 0x9003 is DateTimeOriginal, 0x9004 is DateTimeDigitized
                if 0x9003 in exif_data:
                    timestamp_str = exif_data[0x9003]
                elif 0x9004 in exif_data:
                    timestamp_str = exif_data[0x9004]
                else:
                    timestamp_str = None

                if timestamp_str:
                    # EXIF date format: YYYY:MM:DD HH:MM:SS
                    timestamp = datetime.strptime(timestamp_str, "%Y:%m:%d %H:%M:%S")
    except Exception as e:
        # print(f"Could not read EXIF for {original_path}: {e}") # Uncomment for debugging
        pass

    if not timestamp:
        # Fallback to file modification time if EXIF not found or error
        timestamp = datetime.fromtimestamp(os.path.getmtime(original_path))
    photo["timestamp"] = timestamp

    if not os.path.exists(low_res_path):
        try:
            with Image.open(original_path) as img:
                # Resize to 400px width, maintaining aspect ratio
                width, height = img.size
                new_width = 400
                new_height = int(new_width * height / width)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                img.save(low_res_path)
                print(f"Generated low-res image: {low_res_path}")
        except Exception as e:
            print(f"Error processing image {original_path}: {e}")
    photo["low_res_src"] = low_res_path

# Sort photographs by timestamp (newest first)
data["photographs"].sort(key=lambda x: x["timestamp"], reverse=True)

# Render photography.html
template = env.get_template("photography.html")
output = template.render(data=data)
with open("photography.html", "w") as f:
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
            "photography.html",
        ],
        check=True,
    )
    print("Successfully formatted HTML files with Prettier.")
except subprocess.CalledProcessError as e:
    print(f"Error formatting HTML files with Prettier: {e}")
except FileNotFoundError:
    print("Prettier (npx) not found. Please ensure Node.js and Prettier are installed.")

