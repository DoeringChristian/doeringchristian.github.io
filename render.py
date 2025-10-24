import yaml
from jinja2 import Environment, FileSystemLoader
from omegaconf import OmegaConf
import subprocess
import os
from PIL import Image
import glob
from datetime import datetime

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

# Re-introduce automatic discovery for photography images
PHOTO_DIR = "assets/photo"
if "photographs" not in data or not isinstance(data["photographs"], list):
    data["photographs"] = []

existing_photo_sources = {
    photo["original_src"]
    for photo in data["photographs"]
    if isinstance(photo, dict) and "original_src" in photo
}

for ext in ["*.jpg", "*.jpeg", "*.png", "*.gif"]:
    for photo_path in glob.glob(os.path.join(PHOTO_DIR, ext)):
        if photo_path not in existing_photo_sources:
            low_res_path = process_image_for_low_res(photo_path)
            data["photographs"].append(
                {"original_src": photo_path, "low_res_src": low_res_path}
            )
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
if "photographs" in data:
    for photo_data in data["photographs"]:
        original_path = photo_data["original_src"]

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
                        timestamp = datetime.strptime(
                            timestamp_str, "%Y:%m:%d %H:%M:%S"
                        )
        except Exception as e:
            # print(f"Could not read EXIF for {original_path}: {e}") # Uncomment for debugging
            pass

        if not timestamp:
            # Fallback to file modification time if EXIF not found or error
            timestamp = datetime.fromtimestamp(os.path.getmtime(original_path))
        photo_data["timestamp"] = timestamp

# Sort photographs by timestamp (newest first)
data["photographs"].sort(key=lambda x: x["timestamp"], reverse=True)

# Calculate masonry layout for photography with multiple column configurations
def calculate_masonry_layout(photos, num_columns, total_width_vw, gap_vw):
    """Calculate masonry layout for given column configuration"""
    column_width_vw = (total_width_vw - (num_columns - 1) * gap_vw) / num_columns
    column_heights_vw = [0] * num_columns
    layouts = []

    for photo_data in photos:
        try:
            with Image.open(photo_data["original_src"]) as img:
                width, height = img.size
                # Find the shortest column
                min_height_vw = min(column_heights_vw)
                col_index = column_heights_vw.index(min_height_vw)

                # Scale image to fit column width
                scale_factor = column_width_vw / width
                new_height_vw = height * scale_factor

                # Position the image in vw units
                x_pos_vw = col_index * (column_width_vw + gap_vw)
                y_pos_vw = min_height_vw

                layouts.append({
                    "left": x_pos_vw,
                    "top": y_pos_vw,
                    "width": column_width_vw,
                    "height": new_height_vw,
                })

                # Update column height
                column_heights_vw[col_index] += new_height_vw + gap_vw

        except Exception as e:
            print(f"Could not process image for masonry: {e}")
            layouts.append({"left": 0, "top": 0, "width": 0, "height": 0})

    total_height_vw = max(column_heights_vw) if column_heights_vw else 0
    return layouts, total_height_vw, total_width_vw


if "photographs" in data:
    # Calculate layouts for different screen sizes
    # 3 columns for desktop (>768px)
    layouts_3col, height_3col, width_3col = calculate_masonry_layout(
        data["photographs"], num_columns=3, total_width_vw=90, gap_vw=0.5
    )

    # 2 columns for tablet (481px-768px)
    layouts_2col, height_2col, width_2col = calculate_masonry_layout(
        data["photographs"], num_columns=2, total_width_vw=95, gap_vw=0.5
    )

    # 1 column for mobile (≤480px)
    layouts_1col, height_1col, width_1col = calculate_masonry_layout(
        data["photographs"], num_columns=1, total_width_vw=98, gap_vw=0.5
    )

    # Apply layouts to each photo using CSS custom properties
    for i, photo_data in enumerate(data["photographs"]):
        layout_3 = layouts_3col[i]
        layout_2 = layouts_2col[i]
        layout_1 = layouts_1col[i]

        photo_data["style"] = (
            f"--left-3col: {layout_3['left']}vw; --top-3col: {layout_3['top']}vw; "
            f"--width-3col: {layout_3['width']}vw; --height-3col: {layout_3['height']}vw; "
            f"--left-2col: {layout_2['left']}vw; --top-2col: {layout_2['top']}vw; "
            f"--width-2col: {layout_2['width']}vw; --height-2col: {layout_2['height']}vw; "
            f"--left-1col: {layout_1['left']}vw; --top-1col: {layout_1['top']}vw; "
            f"--width-1col: {layout_1['width']}vw; --height-1col: {layout_1['height']}vw;"
        )

    # Store gallery heights for different layouts
    data["gallery_style"] = (
        f"--height-3col: {height_3col}vw; --width-3col: {width_3col}vw; "
        f"--height-2col: {height_2col}vw; --width-2col: {width_2col}vw; "
        f"--height-1col: {height_1col}vw; --width-1col: {width_1col}vw;"
    )



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
