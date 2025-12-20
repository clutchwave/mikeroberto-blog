#!/usr/bin/env python3
"""
Add Image Dimensions to Frontmatter

Extracts dimensions from local images and adds them to post frontmatter
to satisfy Astro's image optimization requirements.
"""

import os
import re
import subprocess
from pathlib import Path
import yaml

# Configuration
ASTRO_PROJECT = Path.home() / "perl" / "astro" / "mikeroberto-astro"
POSTS_DIR = ASTRO_PROJECT / "src" / "data" / "post"
IMAGES_DIR = ASTRO_PROJECT / "public" / "images"

def get_image_dimensions(image_path):
    """Get image dimensions using ImageMagick identify."""
    try:
        result = subprocess.run(
            ['identify', '-format', '%w %h', str(image_path)],
            capture_output=True,
            text=True,
            check=True
        )
        width, height = result.stdout.strip().split()
        return int(width), int(height)
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError) as e:
        print(f"   ⚠️  Could not get dimensions for {image_path.name}: {e}")
        return None, None

def extract_frontmatter(content):
    """Extract YAML frontmatter from markdown content."""
    # Match frontmatter between --- markers
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not match:
        return None, content
    
    frontmatter_text = match.group(1)
    body = content[match.end():]
    
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        return frontmatter, body
    except yaml.YAMLError as e:
        print(f"   ⚠️  YAML parse error: {e}")
        return None, content

def rebuild_frontmatter(frontmatter):
    """Rebuild frontmatter as YAML string."""
    # Use safe_dump with proper formatting
    yaml_str = yaml.dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=1000  # Prevent line wrapping
    )
    return f"---\n{yaml_str}---\n"

def process_post(md_file):
    """Process a single blog post to add image dimensions."""
    content = md_file.read_text(encoding='utf-8')
    frontmatter, body = extract_frontmatter(content)
    
    if not frontmatter:
        return False
    
    updated = False
    
    # Check if post has a featured image
    if 'image' in frontmatter and isinstance(frontmatter['image'], str):
        image_path_str = frontmatter['image']
        
        # Only process /images/ paths (our local images)
        if image_path_str.startswith('/images/'):
            # Check if dimensions already exist
            if not isinstance(frontmatter.get('image'), dict):
                # Convert string to dict with src
                relative_path = image_path_str.lstrip('/images/')
                full_path = IMAGES_DIR / relative_path
                
                if full_path.exists():
                    width, height = get_image_dimensions(full_path)
                    
                    if width and height:
                        # Convert image to object with dimensions
                        frontmatter['image'] = {
                            'src': image_path_str,
                            'width': width,
                            'height': height
                        }
                        updated = True
                        print(f"   ✓ Added dimensions: {width}x{height} for {full_path.name}")
                    else:
                        print(f"   ✗ Could not get dimensions for {full_path.name}")
                else:
                    print(f"   ⚠️  Image not found: {full_path}")
    
    # Write updated content if changed
    if updated:
        new_content = rebuild_frontmatter(frontmatter) + body
        md_file.write_text(new_content, encoding='utf-8')
        return True
    
    return False

def main():
    print("=" * 70)
    print("📏 Adding Image Dimensions to Frontmatter")
    print("=" * 70)
    print()
    
    # Check if imagemagick is installed
    try:
        subprocess.run(['identify', '--version'], capture_output=True, check=True)
    except FileNotFoundError:
        print("❌ ImageMagick not found!")
        print("   Install with: sudo apt install imagemagick")
        return
    
    print(f"📂 Scanning posts in: {POSTS_DIR}")
    print()
    
    posts_processed = 0
    posts_updated = 0
    
    for md_file in sorted(POSTS_DIR.rglob("*.md")):
        posts_processed += 1
        relative_path = md_file.relative_to(POSTS_DIR)
        print(f"Processing: {relative_path}")
        
        if process_post(md_file):
            posts_updated += 1
    
    print()
    print("=" * 70)
    print(f"✅ Complete!")
    print("=" * 70)
    print(f"   📝 Posts processed: {posts_processed}")
    print(f"   ✏️  Posts updated: {posts_updated}")
    print()
    print("Next: Test with npm run dev")
    print()

if __name__ == "__main__":
    main()
