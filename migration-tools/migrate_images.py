#!/usr/bin/env python3
"""
Smart Image Migration Script for Mike Roberto's Astro Blog

This script:
1. Scans all markdown files to find referenced WordPress images
2. Extracts only those images from the tarball
3. Copies them to public/images/ with organized structure
4. Updates all markdown references to use local paths
5. Reports unused images for review
"""

import os
import re
import tarfile
from pathlib import Path
from collections import defaultdict

# Configuration
ASTRO_PROJECT = Path.home() / "perl" / "astro" / "mikeroberto-astro"
POSTS_DIR = ASTRO_PROJECT / "src" / "data" / "post"
IMAGES_DIR = ASTRO_PROJECT / "public" / "images"
TARBALL = Path.home() / "priceplow" / "mikeroberto" / "uploads_originals_only.tar.gz"

# WordPress image URL patterns
WP_IMAGE_PATTERNS = [
    r'https?://www\.mikeroberto\.com/wp-content/uploads/([^\s\)"]+)',
    r'!\[([^\]]*)\]\(https?://www\.mikeroberto\.com/wp-content/uploads/([^\)]+)\)',
]

def find_referenced_images():
    """Scan all markdown files and find referenced WordPress images."""
    print("🔍 Scanning markdown files for image references...")
    
    referenced_images = set()
    file_count = 0
    
    for md_file in POSTS_DIR.rglob("*.md"):
        file_count += 1
        content = md_file.read_text(encoding='utf-8')
        
        # Find all WordPress image URLs
        for pattern in WP_IMAGE_PATTERNS:
            matches = re.findall(pattern, content)
            for match in matches:
                # Handle tuple results from groups
                if isinstance(match, tuple):
                    image_path = match[-1]  # Last group is the path
                else:
                    image_path = match
                
                # Clean up the path
                image_path = image_path.strip().rstrip('/')
                referenced_images.add(image_path)
    
    print(f"   Found {len(referenced_images)} unique images in {file_count} posts")
    return referenced_images

def get_tarball_contents():
    """Get list of all files in the tarball."""
    print(f"📦 Reading tarball contents: {TARBALL}")
    
    with tarfile.open(TARBALL, 'r:gz') as tar:
        members = {m.name.lstrip('./'): m for m in tar.getmembers() if m.isfile()}
    
    print(f"   Found {len(members)} files in tarball")
    return members

def match_images(referenced, tarball_contents):
    """Match referenced images to tarball contents."""
    print("🔗 Matching referenced images to tarball files...")
    
    matches = {}
    unmatched = []
    
    for ref_image in referenced:
        # Try exact match
        if ref_image in tarball_contents:
            matches[ref_image] = ref_image
            continue
        
        # Try without leading slash
        if ref_image.lstrip('/') in tarball_contents:
            matches[ref_image] = ref_image.lstrip('/')
            continue
        
        # Try just the filename (in case it's at root of tarball)
        filename = os.path.basename(ref_image)
        if filename in tarball_contents:
            matches[ref_image] = filename
            continue
        
        # No match found
        unmatched.append(ref_image)
    
    print(f"   ✅ Matched: {len(matches)}")
    print(f"   ❌ Unmatched: {len(unmatched)}")
    
    if unmatched:
        print("\n⚠️  Unmatched images (may need manual review):")
        for img in sorted(unmatched)[:10]:  # Show first 10
            print(f"      {img}")
        if len(unmatched) > 10:
            print(f"      ... and {len(unmatched) - 10} more")
    
    return matches, unmatched

def extract_images(matches, tarball_contents):
    """Extract matched images to public/images/."""
    print(f"\n📤 Extracting {len(matches)} images to {IMAGES_DIR}")
    
    # Create images directory
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    with tarfile.open(TARBALL, 'r:gz') as tar:
        for ref_path, tar_path in matches.items():
            tar_member = tarball_contents[tar_path]
            
            # Determine output path
            # Keep year/month structure if it exists, otherwise use flat structure
            if '/' in tar_path:
                # Has directory structure, preserve it
                output_path = IMAGES_DIR / tar_path
            else:
                # Flat file, put it at root of images/
                output_path = IMAGES_DIR / os.path.basename(tar_path)
            
            # Create parent directories
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Extract file
            with tar.extractfile(tar_member) as source:
                output_path.write_bytes(source.read())
            
            print(f"   ✓ {tar_path}")
    
    print(f"\n✅ Extracted {len(matches)} images")

def update_markdown_files(matches):
    """Update all markdown files to use local image paths."""
    print("\n✏️  Updating markdown files...")
    
    files_updated = 0
    replacements = 0
    
    # Build replacement map
    # ref_path -> local_path
    replacement_map = {}
    for ref_path, tar_path in matches.items():
        if '/' in tar_path:
            local_path = f"/images/{tar_path}"
        else:
            local_path = f"/images/{os.path.basename(tar_path)}"
        
        # Handle both with and without leading slash in reference
        replacement_map[ref_path] = local_path
        replacement_map['/' + ref_path] = local_path
    
    for md_file in POSTS_DIR.rglob("*.md"):
        content = md_file.read_text(encoding='utf-8')
        original_content = content
        
        # Replace WordPress URLs with local paths
        for old_path, new_path in replacement_map.items():
            # Pattern 1: Markdown images ![alt](url)
            content = re.sub(
                rf'!\[([^\]]*)\]\(https?://www\.mikeroberto\.com/wp-content/uploads/{re.escape(old_path)}\)',
                rf'![\1]({new_path})',
                content
            )
            
            # Pattern 2: HTML img tags
            content = re.sub(
                rf'src=["\']https?://www\.mikeroberto\.com/wp-content/uploads/{re.escape(old_path)}["\']',
                f'src="{new_path}"',
                content
            )
            
            # Pattern 3: Just the URL (in case it appears without markup)
            content = re.sub(
                rf'https?://www\.mikeroberto\.com/wp-content/uploads/{re.escape(old_path)}',
                new_path,
                content
            )
        
        if content != original_content:
            md_file.write_text(content, encoding='utf-8')
            files_updated += 1
            # Count actual replacements
            replacements += original_content.count('www.mikeroberto.com/wp-content/uploads')
            replacements -= content.count('www.mikeroberto.com/wp-content/uploads')
    
    print(f"   ✅ Updated {files_updated} files ({replacements} replacements)")

def report_unused_images(tarball_contents, matches):
    """Report which images in the tarball weren't used."""
    print("\n📊 Unused images report:")
    
    used_tar_paths = set(matches.values())
    all_tar_paths = set(tarball_contents.keys())
    unused = all_tar_paths - used_tar_paths
    
    # Filter out directories (already done in get_tarball_contents, but double-check)
    unused_files = [f for f in unused if not f.endswith('/')]
    
    print(f"   📦 Total in tarball: {len(all_tar_paths)}")
    print(f"   ✅ Used in posts: {len(used_tar_paths)}")
    print(f"   📁 Unused: {len(unused_files)}")
    
    if unused_files:
        # Save unused list to file
        unused_file = ASTRO_PROJECT / "migration-tools" / "unused_images.txt"
        unused_file.parent.mkdir(parents=True, exist_ok=True)
        unused_file.write_text('\n'.join(sorted(unused_files)))
        print(f"\n   💾 Full list saved to: {unused_file}")
        
        # Show sample
        print("\n   Sample unused images:")
        for img in sorted(unused_files)[:15]:
            print(f"      {img}")
        if len(unused_files) > 15:
            print(f"      ... and {len(unused_files) - 15} more")

def main():
    print("=" * 70)
    print("🖼️  Smart Image Migration for Mike Roberto's Astro Blog")
    print("=" * 70)
    print()
    
    # Step 1: Find referenced images
    referenced = find_referenced_images()
    
    if not referenced:
        print("❌ No images found in markdown files!")
        return
    
    # Step 2: Get tarball contents
    tarball_contents = get_tarball_contents()
    
    # Step 3: Match images
    matches, unmatched = match_images(referenced, tarball_contents)
    
    if not matches:
        print("❌ No images could be matched!")
        return
    
    # Step 4: Extract images
    extract_images(matches, tarball_contents)
    
    # Step 5: Update markdown files
    update_markdown_files(matches)
    
    # Step 6: Report unused images
    report_unused_images(tarball_contents, matches)
    
    print("\n" + "=" * 70)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 70)
    print(f"\n📁 Images location: {IMAGES_DIR}")
    print(f"📝 Posts location: {POSTS_DIR}")
    print("\nNext steps:")
    print("1. Test locally: npm run dev")
    print("2. Check that images load correctly")
    print("3. git add public/images/")
    print("4. git commit -m 'Migrate images to local repository'")
    print("5. git push")
    print()

if __name__ == "__main__":
    main()
