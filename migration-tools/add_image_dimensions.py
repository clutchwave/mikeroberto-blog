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
        return None, None, content
    
    frontmatter_text = match.group(1)
    frontmatter_end = match.end()
    body = content[frontmatter_end:]
    
    return frontmatter_text, frontmatter_end, body

def process_image_line(line, images_dir):
    """Process a line containing 'image:' field and add dimensions if needed."""
    # Check if this is a simple image: line
    simple_match = re.search(r'image:\s*["\']?(/images/[^"\']+)["\']?', line)
    
    if simple_match and 'width:' not in line and 'height:' not in line:
        # Simple format without dimensions - convert to object format
        image_path = simple_match.group(1)
        filename = image_path.replace('/images/', '')
        full_path = images_dir / filename
        
        if not full_path.exists():
            print(f"   ⚠️  Image not found: {filename}")
            return None
        
        width, height = get_image_dimensions(full_path)
        if width is None or height is None:
            return None
        
        ext = full_path.suffix.lower().lstrip('.')
        if ext == 'jpg':
            ext = 'jpeg'
        
        indent = len(line) - len(line.lstrip())
        indent_str = ' ' * indent
        
        new_lines = [
            f'{indent_str}image:\n',
            f'{indent_str}  src: "{image_path}"\n',
            f'{indent_str}  width: {width}\n',
            f'{indent_str}  height: {height}\n',
            f'{indent_str}  format: "{ext}"\n'
        ]
        
        return ('convert', new_lines, filename, width, height)
    
    return None

def process_frontmatter_object(lines, start_idx, images_dir):
    """Process an image object that might be missing format."""
    # Check if we're in an image: object
    if not lines[start_idx].strip().startswith('image:'):
        return None
    
    # Look ahead for src:, width:, height:, format:
    has_src = False
    has_width = False
    has_height = False
    has_format = False
    src_value = None
    
    i = start_idx + 1
    indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        
        line_indent = len(line) - len(line.lstrip())
        if line_indent <= indent:
            # Back to same or lower indent level
            break
        
        if 'src:' in line:
            has_src = True
            match = re.search(r'src:\s*["\']?(/images/[^"\']+)["\']?', line)
            if match:
                src_value = match.group(1)
        elif 'width:' in line:
            has_width = True
        elif 'height:' in line:
            has_height = True
        elif 'format:' in line:
            has_format = True
        
        i += 1
    
    # If we have src, width, height but no format, add format
    if has_src and has_width and has_height and not has_format and src_value:
        filename = src_value.replace('/images/', '')
        full_path = images_dir / filename
        
        if not full_path.exists():
            print(f"   ⚠️  Image not found: {filename}")
            return None
        
        ext = full_path.suffix.lower().lstrip('.')
        if ext == 'jpg':
            ext = 'jpeg'
        
        indent_str = ' ' * (indent + 2)
        format_line = f'{indent_str}format: "{ext}"\n'
        
        return ('add_format', i, format_line, filename)
    
    return None

def process_post(md_file):
    """Process a single blog post to add image dimensions."""
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    frontmatter_text, frontmatter_end, body = extract_frontmatter(content)
    
    if frontmatter_text is None:
        print(f"   ⚠️  No frontmatter found")
        return False
    
    # Process frontmatter line by line
    lines = frontmatter_text.split('\n')
    new_lines = []
    modified = False
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        if line.strip().startswith('image:'):
            # Try simple format conversion
            result = process_image_line(line, IMAGES_DIR)
            if result and result[0] == 'convert':
                _, new_lines_to_add, filename, width, height = result
                new_lines.extend(new_lines_to_add)
                modified = True
                print(f"   ✓ Converted to object format with dimensions: {width}x{height} for {filename}")
                i += 1
                continue
            
            # Try adding format to existing object
            result = process_frontmatter_object(lines, i, IMAGES_DIR)
            if result and result[0] == 'add_format':
                _, insert_pos, format_line, filename = result
                # Copy lines up to insert position
                for j in range(i, insert_pos):
                    new_lines.append(lines[j] + '\n')
                # Insert format line
                new_lines.append(format_line)
                modified = True
                print(f"   ✓ Added format field for {filename}")
                i = insert_pos
                continue
        
        new_lines.append(line + '\n')
        i += 1
    
    if not modified:
        return False
    
    # Rebuild content
    new_frontmatter = '---\n' + ''.join(new_lines).rstrip('\n') + '\n---\n'
    new_content = new_frontmatter + body
    
    # Write back
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

def main():
    print("=" * 70)
    print("📏 Adding Image Dimensions to Frontmatter")
    print("=" * 70)
    print()
    
    # Check ImageMagick is installed
    try:
        subprocess.run(['identify', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: ImageMagick 'identify' command not found.")
        print("   Install with: sudo apt-get install imagemagick")
        return 1
    
    if not POSTS_DIR.exists():
        print(f"❌ Error: Posts directory not found: {POSTS_DIR}")
        return 1
    
    if not IMAGES_DIR.exists():
        print(f"❌ Error: Images directory not found: {IMAGES_DIR}")
        return 1
    
    print(f"📂 Scanning posts in: {POSTS_DIR}")
    print()
    
    # Find all markdown files
    md_files = list(POSTS_DIR.rglob('*.md'))
    
    processed = 0
    updated = 0
    
    for md_file in sorted(md_files):
        rel_path = md_file.relative_to(POSTS_DIR)
        print(f"Processing: {rel_path}")
        
        try:
            if process_post(md_file):
                updated += 1
            processed += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print()
    print("=" * 70)
    print("✅ Complete!")
    print("=" * 70)
    print(f"   📝 Posts processed: {processed}")
    print(f"   ✏️  Posts updated: {updated}")
    print()
    
    if updated > 0:
        print("🔄 Test your site:")
        print("   npm run dev")
    
    return 0

if __name__ == '__main__':
    exit(main())
