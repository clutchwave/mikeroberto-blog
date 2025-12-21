#!/usr/bin/env python3
"""
Analyze images in WordPress export and compare with local files
"""

import xml.etree.ElementTree as ET
import re
from pathlib import Path
from urllib.parse import urlparse
import argparse

NS = {
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'wp': 'http://wordpress.org/export/1.2/',
}

def extract_images_from_content(content):
    """Extract all image URLs from HTML content"""
    if not content:
        return []
    
    images = []
    
    # Find <img> tags
    img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
    images.extend(re.findall(img_pattern, content))
    
    # Find markdown images (in case there are any)
    md_pattern = r'!\[[^\]]*\]\(([^\)]+)\)'
    images.extend(re.findall(md_pattern, content))
    
    return images

def analyze_wordpress_images(xml_file, local_images_dir):
    """Analyze all images used in WordPress content"""
    
    print(f"Analyzing images in {xml_file}...")
    print(f"Local images directory: {local_images_dir}\n")
    
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Collect all images from posts
    all_images = []
    
    for item in root.findall('.//item'):
        post_type = item.find('wp:post_type', NS)
        if post_type is not None and post_type.text == 'post':
            status = item.find('wp:status', NS)
            if status is not None and status.text == 'publish':
                content_elem = item.find('content:encoded', NS)
                if content_elem is not None and content_elem.text:
                    images = extract_images_from_content(content_elem.text)
                    all_images.extend(images)
    
    # Filter to only WordPress uploads
    wp_images = []
    for img_url in all_images:
        if 'wp-content/uploads' in img_url:
            wp_images.append(img_url)
    
    # Deduplicate
    wp_images = list(set(wp_images))
    
    print(f"Found {len(wp_images)} unique WordPress image URLs (including thumbnails)\n")
    
    # Strip dimensions to get original filenames
    original_images = {}
    for img_url in wp_images:
        filename = img_url.split('/')[-1]
        # Strip WordPress thumbnail dimensions
        original_filename = re.sub(r'-\d+x\d+(\.[a-zA-Z]+)$', r'\1', filename)
        
        # Store the original URL for downloading
        # Reconstruct URL with original filename
        url_without_filename = img_url.rsplit('/', 1)[0]
        original_url = f"{url_without_filename}/{original_filename}"
        
        original_images[original_filename] = original_url
    
    print(f"Stripped to {len(original_images)} unique ORIGINAL images (thumbnails removed)\n")
    print("=" * 70)
    print("IMAGE INVENTORY")
    print("=" * 70)
    
    # Get local images
    local_images_path = Path(local_images_dir)
    local_files = set()
    
    if local_images_path.exists():
        for img_file in local_images_path.rglob('*'):
            if img_file.is_file():
                local_files.add(img_file.name)
    
    print(f"\nLocal images found: {len(local_files)}")
    
    # Analyze each original image
    missing = []
    present = []
    
    for filename, img_url in sorted(original_images.items()):
        if filename in local_files:
            present.append((filename, img_url))
        else:
            missing.append((filename, img_url))
    
    print(f"\n✓ Already local: {len(present)} images")
    print(f"✗ Need download: {len(missing)} images")
    
    # Show missing images
    if missing:
        print("\n" + "=" * 70)
        print("ORIGINAL IMAGES TO DOWNLOAD")
        print("=" * 70)
        for filename, img_url in sorted(missing):
            print(f"  {filename}")
            print(f"    → {img_url}")
    
    # Generate download script
    if missing:
        print("\n" + "=" * 70)
        print("DOWNLOAD SCRIPT")
        print("=" * 70)
        print("\nSave this as download-missing-images.sh:\n")
        print("#!/bin/bash")
        print(f"cd {local_images_dir}")
        print()
        for filename, img_url in sorted(missing):
            # Clean URL (remove any query strings)
            clean_url = img_url.split('?')[0]
            print(f"wget -O '{filename}' '{clean_url}'")
        print()
        print("echo 'Download complete!'")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total WordPress image URLs: {len(wp_images)} (including thumbnails)")
    print(f"Unique original images: {len(original_images)}")
    print(f"Already local: {len(present)}")
    print(f"Need download: {len(missing)}")
    
    if len(missing) == 0:
        print("\n✓ All images are already local!")
        print("  Ready to convert with --local-images flag")
    else:
        print(f"\n⚠ Need to download {len(missing)} images first")
        print("  1. Run the download script above")
        print("  2. Then convert with --local-images flag")
    
    return {
        'total': len(wp_images),
        'originals': len(original_images),
        'present': len(present),
        'missing': len(missing),
        'missing_list': missing
    }

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Analyze images in WordPress export'
    )
    parser.add_argument('xml_file', help='WordPress XML export file')
    parser.add_argument('--local-images-dir', default='public/images',
                       help='Local images directory (default: public/images)')
    
    args = parser.parse_args()
    
    analyze_wordpress_images(args.xml_file, args.local_images_dir)
