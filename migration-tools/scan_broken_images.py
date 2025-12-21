#!/usr/bin/env python3
"""
Scan blog posts for broken images and remove them.
Handles:
- HTTP errors (404, 500, etc.)
- Connection timeouts
- Photobucket "image unavailable" placeholders
"""

import os
import re
import sys
import time
from pathlib import Path
from typing import List, Tuple, Set
import requests
from urllib.parse import urlparse

# Known Photobucket placeholder characteristics
PHOTOBUCKET_PLACEHOLDER_SIGNATURES = [
    "photobucket.com",  # Domain check
    "image is currently unavailable",  # Text in alt
]

class ImageScanner:
    def __init__(self, posts_dir: str, dry_run: bool = True, check_local: bool = False, check_photobucket: bool = False):
        self.posts_dir = Path(posts_dir)
        self.dry_run = dry_run
        self.check_local = check_local
        self.check_photobucket = check_photobucket
        self.broken_images = []
        self.local_missing = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # Cache for URL checks (avoid re-checking same URLs)
        self.url_cache = {}
        
        # Find project root (should contain public/ directory)
        self.project_root = self.posts_dir.parent.parent.parent  # posts_dir is src/data/post
        self.public_dir = self.project_root / 'public'
        
    def extract_images_from_markdown(self, content: str) -> List[Tuple[str, str, int, int]]:
        """
        Extract all image URLs from markdown content.
        Returns: [(url, full_match, start_pos, end_pos), ...]
        """
        images = []
        
        # Pattern 1: Markdown images ![alt](url)
        md_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        for match in re.finditer(md_pattern, content):
            images.append((
                match.group(2),  # URL
                match.group(0),  # Full match
                match.start(),
                match.end()
            ))
        
        # Pattern 2: HTML img tags
        html_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*/?>'
        for match in re.finditer(html_pattern, content, re.IGNORECASE):
            images.append((
                match.group(1),  # URL
                match.group(0),  # Full match
                match.start(),
                match.end()
            ))
        
        return images
    
    def extract_figure_block(self, content: str, img_start: int) -> Tuple[str, int, int]:
        """
        If image is inside a <figure> tag, extract the entire figure block.
        Returns: (figure_content, start_pos, end_pos) or (None, -1, -1)
        """
        # Search backwards for <figure
        figure_start = content.rfind('<figure', 0, img_start)
        if figure_start == -1:
            return (None, -1, -1)
        
        # Search forwards for </figure>
        figure_end = content.find('</figure>', img_start)
        if figure_end == -1:
            return (None, -1, -1)
        
        figure_end += len('</figure>')
        return (content[figure_start:figure_end], figure_start, figure_end)
    
    def is_photobucket_placeholder(self, url: str, response: requests.Response = None) -> bool:
        """
        Detect if image is a Photobucket "unavailable" placeholder.
        Conservative detection: only flags if very specific conditions match.
        The placeholder is exactly 500x375 pixels and ~4-5KB.
        """
        if not self.check_photobucket:
            return False
            
        # Check URL domain
        if 'photobucket.com' in url.lower():
            # If we have response, check content length
            if response and response.status_code == 200:
                content_length = len(response.content)
                # Photobucket placeholder is specifically ~4-5KB (4000-6000 bytes)
                # Being very conservative here to avoid false positives
                if 4000 <= content_length <= 6000:
                    # Could add additional checks here like:
                    # - Check if it's a PNG (placeholder is PNG)
                    # - Check actual image dimensions with PIL/Pillow
                    return True
        return False
    
    def is_local_url(self, url: str) -> bool:
        """
        Check if URL is a local/relative URL (starts with /).
        """
        return url.startswith('/')
    
    def check_local_file(self, url: str) -> Tuple[bool, str]:
        """
        Check if local file exists in public directory.
        Returns: (exists, reason)
        """
        # Remove leading slash
        rel_path = url.lstrip('/')
        full_path = self.public_dir / rel_path
        
        if full_path.exists():
            return (True, "Local file exists")
        else:
            return (False, f"Local file not found: {full_path}")
    
    
    def check_url(self, url: str) -> Tuple[bool, str]:
        """
        Check if URL is valid and returns 200.
        Returns: (is_valid, reason)
        """
        # Handle local URLs
        if self.is_local_url(url):
            if self.check_local:
                return self.check_local_file(url)
            else:
                return (True, "Local URL (skipped)")
        
        # Check cache first
        if url in self.url_cache:
            return self.url_cache[url]
        
        try:
            # HEAD request first (faster)
            response = self.session.head(url, timeout=10, allow_redirects=True)
            
            # Some servers don't support HEAD, try GET if needed
            if response.status_code == 405:
                response = self.session.get(url, timeout=10, stream=True)
                response.close()
            
            if response.status_code == 200:
                # Check for Photobucket placeholder
                if self.is_photobucket_placeholder(url, response):
                    result = (False, "Photobucket placeholder")
                else:
                    result = (True, "OK")
            else:
                result = (False, f"HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            result = (False, "Timeout")
        except requests.exceptions.ConnectionError:
            result = (False, "Connection error")
        except requests.exceptions.TooManyRedirects:
            result = (False, "Too many redirects")
        except Exception as e:
            result = (False, f"Error: {str(e)}")
        
        # Cache result
        self.url_cache[url] = result
        return result
    
    def remove_image_from_content(self, content: str, img_start: int, img_end: int) -> str:
        """
        Remove image from content. If it's in a figure, remove the whole figure.
        Otherwise just remove the image line.
        """
        # Check if image is in a figure block
        figure_content, fig_start, fig_end = self.extract_figure_block(content, img_start)
        
        if figure_content:
            # Remove entire figure block
            # Also remove the newline after if present
            if fig_end < len(content) and content[fig_end] == '\n':
                fig_end += 1
            return content[:fig_start] + content[fig_end:]
        else:
            # Remove just the image line
            # Find the line boundaries
            line_start = content.rfind('\n', 0, img_start)
            if line_start == -1:
                line_start = 0
            else:
                line_start += 1  # Skip the newline
            
            line_end = content.find('\n', img_end)
            if line_end == -1:
                line_end = len(content)
            else:
                line_end += 1  # Include the newline
            
            return content[:line_start] + content[line_end:]
    
    def process_file(self, file_path: Path) -> int:
        """
        Process a single markdown file.
        Returns: number of broken images found
        """
        print(f"\n📄 Processing: {file_path.relative_to(self.posts_dir.parent)}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        content = original_content
        images = self.extract_images_from_markdown(content)
        
        if not images:
            print("   No images found")
            return 0
        
        # Count local vs external
        local_images = sum(1 for url, _, _, _ in images if self.is_local_url(url))
        external_images = len(images) - local_images
        
        if local_images > 0 and not self.check_local:
            print(f"   Found {len(images)} images ({local_images} local, {external_images} external)")
        else:
            print(f"   Found {len(images)} images")
        
        broken_count = 0
        removed_urls = set()
        
        # Process images in reverse order to maintain positions
        for url, full_match, start, end in reversed(images):
            # Skip if we already removed this URL (duplicate)
            if url in removed_urls:
                continue
            
            # Only log external URLs or if checking local
            if not self.is_local_url(url) or self.check_local:
                print(f"   🔍 Checking: {url[:80]}...")
            
            is_valid, reason = self.check_url(url)
            
            if not is_valid:
                print(f"      ❌ BROKEN: {reason}")
                broken_count += 1
                removed_urls.add(url)
                
                self.broken_images.append({
                    'file': str(file_path.relative_to(self.posts_dir.parent)),
                    'url': url,
                    'reason': reason
                })
                
                if not self.dry_run:
                    # Remove image from content
                    content = self.remove_image_from_content(content, start, end)
                    print(f"      🗑️  Removed from file")
            elif not self.is_local_url(url) or self.check_local:
                # Only log non-local URLs as OK
                print(f"      ✅ OK")
            
            # Be nice to servers (but not for local files)
            if not self.is_local_url(url):
                time.sleep(0.5)
        
        # Write updated content if changes were made
        if not self.dry_run and content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   💾 Updated file (removed {broken_count} images)")
        
        return broken_count
    
    def scan_all_posts(self):
        """
        Scan all markdown files in the posts directory.
        """
        print("🔍 Scanning for broken images...")
        print(f"📁 Posts directory: {self.posts_dir}")
        print(f"🏃 Mode: {'DRY RUN (no changes)' if self.dry_run else 'LIVE (will modify files)'}")
        if not self.check_local:
            print(f"ℹ️  Local images (starting with /) are skipped (use --check-local to verify)")
        else:
            print(f"🔍 Checking local images in: {self.public_dir}")
        if not self.check_photobucket:
            print(f"ℹ️  Photobucket placeholder detection disabled (use --check-photobucket to enable)")
        else:
            print(f"⚠️  Photobucket placeholder detection enabled (may have false positives)")
        print("=" * 80)
        
        total_broken = 0
        total_files = 0
        
        # Walk through all subdirectories
        for md_file in sorted(self.posts_dir.rglob('*.md')):
            total_files += 1
            broken = self.process_file(md_file)
            total_broken += broken
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print(f"Files scanned: {total_files}")
        print(f"Broken images found: {total_broken}")
        
        if self.broken_images:
            print(f"\n🔴 BROKEN IMAGES REPORT:")
            for item in self.broken_images:
                print(f"\n  File: {item['file']}")
                print(f"  URL:  {item['url']}")
                print(f"  Reason: {item['reason']}")
        
        if self.dry_run and self.broken_images:
            print("\n⚠️  This was a DRY RUN - no files were modified")
            print("   Run with --fix to actually remove broken images")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Scan blog posts for broken images and optionally remove them'
    )
    parser.add_argument(
        'posts_dir',
        help='Path to posts directory (e.g., src/data/post)'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Actually remove broken images (default is dry-run)'
    )
    parser.add_argument(
        '--check-local',
        action='store_true',
        help='Also verify local image files exist in public/ directory'
    )
    parser.add_argument(
        '--check-photobucket',
        action='store_true',
        help='Enable Photobucket placeholder detection (conservative, may have false positives)'
    )
    
    args = parser.parse_args()
    
    posts_dir = Path(args.posts_dir)
    if not posts_dir.exists():
        print(f"❌ Error: Directory not found: {posts_dir}")
        sys.exit(1)
    
    scanner = ImageScanner(
        posts_dir, 
        dry_run=not args.fix, 
        check_local=args.check_local,
        check_photobucket=args.check_photobucket
    )
    scanner.scan_all_posts()


if __name__ == '__main__':
    main()
