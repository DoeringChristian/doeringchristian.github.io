import yaml
from jinja2 import Environment, FileSystemLoader
from omegaconf import OmegaConf
import subprocess

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