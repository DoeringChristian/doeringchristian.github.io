# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a static personal profile/portfolio website that uses Python-based template rendering. The site is generated from YAML data and Jinja2 templates, and includes a photography gallery with automatic image processing.

## Build and Development Commands

### Rendering the site
```bash
python render.py
```
This is the main build command. It:
- Loads data from `data.yaml` using OmegaConf (with variable interpolation support)
- Generates low-resolution versions of all images (400px width) in `assets/low_res/`
- Auto-discovers photos from `assets/photo/` directory
- Extracts EXIF timestamps from photographs (falls back to file modification time)
- Sorts photographs by timestamp (newest first)
- Calculates masonry layout positions for photography gallery (3-column grid in vw units)
- Renders `index.html` and `photography.html` from Jinja2 templates
- Formats output with Prettier

### Formatting
```bash
pixi run format
```
Formats HTML and CSS files using Prettier (npm exec).

### Environment setup
This project uses Pixi for dependency management:
```bash
pixi install
```

## Architecture

### Data Flow
1. **data.yaml** → Contains all site content (bio, projects, publications, social links)
   - Supports OmegaConf interpolation (e.g., variable references)
   - Image paths are automatically processed to generate low-res versions

2. **render.py** → Main build script that:
   - Recursively traverses data structure to find image paths
   - Converts image strings to `{original_src, low_res_src}` objects
   - Adds metadata (timestamps, layout positions) to photograph entries
   - Renders templates with processed data

3. **templates/** → Jinja2 templates with inheritance:
   - `base.html`: Master template with theme switcher, Font Awesome icons, CSS links
   - `index.html`: Extends base, includes about/publications/projects components
   - `photography.html`: Extends base, displays masonry gallery
   - `components/`: Reusable template fragments (header, footer, scripts, sections)

### Image Processing Pipeline
Images in `assets/` are automatically processed:
- Low-res versions (400px width) generated in `assets/low_res/` with preserved directory structure
- EXIF data extracted for timestamps (fields 0x9003 DateTimeOriginal, 0x9004 DateTimeDigitized)
- Photos sorted by timestamp descending
- Masonry layout calculated server-side using viewport width units (vw)

### Masonry Layout Calculation
The photography gallery uses a server-side calculated masonry layout:
- 3 columns, 90vw total width, 0.5vw gap
- Shortest-column algorithm places each image
- Absolute positioning with vw units for responsive scaling
- Total gallery height calculated from tallest column

## Key Files
- `data.yaml`: All site content and configuration
- `render.py`: Template rendering and image processing logic (lines 17-38: low-res generation, 44-59: recursive data processing, 138-182: masonry calculation)
- `pixi.toml`: Python and Node.js dependencies (PyYAML, Jinja2, OmegaConf, Pillow)
- `templates/base.html`: Theme switcher stored in localStorage
- `styles/main.css`: Main stylesheet
- `styles/photography.css`: Photography gallery specific styles

## Development Notes
- HTML files (index.html, photography.html) are generated artifacts - edit templates instead
- Low-res images in `assets/low_res/` are auto-generated - don't edit manually
- Theme switching is implemented with `data-theme` attribute on `<html>` element
- Site deployed to `doeringc.de` (CNAME file present)
