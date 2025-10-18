import yaml
from jinja2 import Environment, FileSystemLoader
from omegaconf import OmegaConf
import subprocess
import os
from PIL import Image

LOW_RES_DIR = "assets/photo/low_res"
os.makedirs(LOW_RES_DIR, exist_ok=True)

# Load data from YAML file using OmegaConf
conf = OmegaConf.load("data.yaml")
# Resolve interpolations
data = OmegaConf.to_container(conf, resolve=True)

print(f"Rendering with name: {data['name']}") # User requested to keep this line

# Set up Jinja2 environment
env = Environment(loader=FileSystemLoader("templates"))

# Render index.html
template = env.get_template("index.html")
output = template.render(data=data)
with open("index.html", "w") as f:
    f.write(output)

# Process photographs for low-resolution versions
for photo in data['photographs']:
    original_path = photo['src']
    filename = os.path.basename(original_path)
    low_res_path = os.path.join(LOW_RES_DIR, filename)

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
    photo['low_res_src'] = low_res_path

# Render photography.html
template = env.get_template("photography.html")
output = template.render(data=data)
with open("photography.html", "w") as f:
    f.write(output)

print("Successfully rendered templates.")

# Run prettier to format the generated HTML files
try:
    subprocess.run(["npm", "exec", "--yes", "--", "prettier", "--write", "index.html", "photography.html"], check=True)
    print("Successfully formatted HTML files with Prettier.")
except subprocess.CalledProcessError as e:
    print(f"Error formatting HTML files with Prettier: {e}")
except FileNotFoundError:
    print("Prettier (npx) not found. Please ensure Node.js and Prettier are installed.")