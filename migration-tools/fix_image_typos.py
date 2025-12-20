#!/usr/bin/env python3
"""
Fix image filename typos in frontmatter.

Fixes:
- utism-and-canola-oil.png → autism-and-canola-oil.png
- oybean-oil-scandal.png → soybean-oil-scandal.png
"""

from pathlib import Path

ASTRO_PROJECT = Path.home() / "perl" / "astro" / "mikeroberto-astro"
POSTS_DIR = ASTRO_PROJECT / "src" / "data" / "post"

# Typo fixes
FIXES = {
    'utism-and-canola-oil.png': 'autism-and-canola-oil.png',
    'oybean-oil-scandal.png': 'soybean-oil-scandal.png',
}

def main():
    print("🔧 Fixing image filename typos in frontmatter...")
    print()
    
    fixed_count = 0
    
    for md_file in POSTS_DIR.rglob("*.md"):
        content = md_file.read_text(encoding='utf-8')
        original_content = content
        
        # Apply fixes
        for wrong, correct in FIXES.items():
            if wrong in content:
                content = content.replace(wrong, correct)
                print(f"   ✓ Fixed {wrong} → {correct} in {md_file.name}")
                fixed_count += 1
        
        # Write back if changed
        if content != original_content:
            md_file.write_text(content, encoding='utf-8')
    
    print()
    print(f"✅ Fixed {fixed_count} typos")
    print()

if __name__ == "__main__":
    main()
