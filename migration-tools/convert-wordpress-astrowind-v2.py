#!/usr/bin/env python3
"""
WordPress to AstroWind Migration Script v2.0
Converts WordPress XML export to AstroWind-compatible markdown files

Key improvements:
- Preserves styled <div> elements and other custom HTML
- Properly handles nested lists (no code block conversion)
- Extracts featured images via _thumbnail_id
- Gets SEO descriptions from _aioseo_description
- Converts [caption] shortcodes to <figure> tags
"""

import xml.etree.ElementTree as ET
import re
import html as html_lib
import os
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import argparse

# WordPress XML namespaces
NS = {
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'wp': 'http://wordpress.org/export/1.2/',
    'excerpt': 'http://wordpress.org/export/1.2/excerpt/',
    'dc': 'http://purl.org/dc/elements/1.1/'
}

def extract_featured_image(item, attachments_map):
    """Extract featured image URL from _thumbnail_id"""
    # Find _thumbnail_id in postmeta
    for meta in item.findall('wp:postmeta', NS):
        key = meta.find('wp:meta_key', NS)
        if key is not None and key.text == '_thumbnail_id':
            value = meta.find('wp:meta_value', NS)
            if value is not None and value.text:
                thumbnail_id = value.text
                # Look up attachment URL
                if thumbnail_id in attachments_map:
                    return attachments_map[thumbnail_id]
    return None

def build_attachments_map(root):
    """Build map of attachment_id -> image_url from WordPress export"""
    attachments = {}
    
    for item in root.findall('.//item'):
        post_type = item.find('wp:post_type', NS)
        if post_type is not None and post_type.text == 'attachment':
            post_id = item.find('wp:post_id', NS)
            attachment_url = item.find('wp:attachment_url', NS)
            
            if post_id is not None and attachment_url is not None:
                if post_id.text and attachment_url.text:
                    attachments[post_id.text] = attachment_url.text
    
    print(f"Found {len(attachments)} attachments in WordPress export")
    return attachments

def convert_wordpress_captions(html_content):
    """Convert WordPress [caption] shortcodes to proper HTML figure tags"""
    if not html_content:
        return ""
    
    # Pattern for WordPress caption shortcodes
    # [caption id="..." align="aligncenter" width="..."]<img.../>Caption text[/caption]
    caption_pattern = r'\[caption[^\]]*align="(align(?:center|left|right|none))"[^\]]*\](.*?)\[/caption\]'
    
    def replace_caption(match):
        alignment = match.group(1)  # aligncenter, alignleft, alignright, alignnone
        content = match.group(2).strip()
        
        # Extract image tag (with or without link wrapper)
        img_match = re.search(r'(<a[^>]*>)?(<img[^>]*>)(</a>)?', content, re.DOTALL)
        if not img_match:
            return content  # Can't parse, return as-is
        
        image_html = img_match.group(0)  # Full image (with link if present)
        
        # Extract caption text (everything after the image)
        caption_text = content[img_match.end():].strip()
        
        # Build figure HTML with alignment class
        figure_html = f'<figure class="{alignment}">\n'
        figure_html += f'  {image_html}\n'
        if caption_text:
            figure_html += f'  <figcaption>{caption_text}</figcaption>\n'
        figure_html += '</figure>'
        
        return figure_html
    
    # Replace all caption shortcodes
    content = re.sub(caption_pattern, replace_caption, html_content, flags=re.DOTALL)
    
    return content

def replace_wordpress_image_urls(content, use_local_images=False):
    """Replace WordPress image URLs with local paths if requested"""
    if not use_local_images:
        return content
    
    def replace_image_url(match):
        """Replace WordPress URL and strip thumbnail dimensions"""
        full_url = match.group(0)
        filename = match.group(1)
        
        # Strip WordPress thumbnail dimensions from filename
        # Examples: image-300x300.jpg → image.jpg
        #           image-625x327.png → image.png
        filename = re.sub(r'-\d+x\d+(\.[a-zA-Z]+)$', r'\1', filename)
        
        return f'/images/{filename}'
    
    # Replace WordPress upload URLs with local /images/ paths
    # Pattern: https://www.mikeroberto.com/wp-content/uploads/YYYY/MM/filename.jpg
    # Pattern: https://blog.priceplow.com/wp-content/uploads/YYYY/MM/filename.jpg
    # Replace with: /images/filename.jpg (with dimensions stripped)
    content = re.sub(
        r'https?://(?:www\.)?(?:mikeroberto\.com|blog\.priceplow\.com)/wp-content/uploads/(?:\d{4}/\d{2}/)?([^"\s\)]+)',
        replace_image_url,
        content
    )
    
    return content

def clean_html_to_markdown(html_content, use_local_images=False):
    """Convert WordPress HTML to markdown while preserving styled elements"""
    if not html_content:
        return ""
    
    content = html_content
    
    # FIRST: Replace WordPress image URLs with local paths if requested
    content = replace_wordpress_image_urls(content, use_local_images)
    
    # STEP 1: Protect elements that should remain as HTML
    # These are stored and restored at the end
    protected_elements = {}
    counter = 0
    
    def protect_element(match):
        nonlocal counter
        placeholder = f"___PROTECTED_{counter}___"
        protected_elements[placeholder] = match.group(0)
        counter += 1
        return placeholder
    
    # Protect: <div> with style attribute
    content = re.sub(r'<div[^>]*style=[^>]*>.*?</div>', protect_element, content, flags=re.DOTALL | re.IGNORECASE)
    
    # Protect: <figure> tags (from caption conversion)
    content = re.sub(r'<figure[^>]*>.*?</figure>', protect_element, content, flags=re.DOTALL | re.IGNORECASE)
    
    # Protect: <img> with class or style attributes
    content = re.sub(r'<img[^>]*(class|style)=[^>]*>', protect_element, content, flags=re.IGNORECASE)
    
    # Protect: <blockquote> with class attribute
    content = re.sub(r'<blockquote[^>]*class=[^>]*>.*?</blockquote>', protect_element, content, flags=re.DOTALL | re.IGNORECASE)
    
    # Protect: <iframe>, <embed>, <object>, <script>
    content = re.sub(r'<(iframe|embed|object|script)[^>]*>.*?</\1>', protect_element, content, flags=re.DOTALL | re.IGNORECASE)
    
    # Protect: <ol> or <ul> with class attribute
    content = re.sub(r'<(ol|ul)[^>]*class=[^>]*>.*?</\1>', protect_element, content, flags=re.DOTALL | re.IGNORECASE)
    
    # STEP 2: Convert simple HTML to markdown
    
    # Bold and italic
    content = re.sub(r'<strong>(.*?)</strong>', r'**\1**', content, flags=re.DOTALL)
    content = re.sub(r'<b>(.*?)</b>', r'**\1**', content, flags=re.DOTALL)
    content = re.sub(r'<em>(.*?)</em>', r'*\1*', content, flags=re.DOTALL)
    content = re.sub(r'<i>(.*?)</i>', r'*\1*', content, flags=re.DOTALL)
    
    # Links
    content = re.sub(r'<a\s+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r'[\2](\1)', content, flags=re.DOTALL)
    
    # Simple images (without class/style - those are protected)
    content = re.sub(
        r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*alt=["\']([^"\']*)["\'][^>]*/*>',
        r'![\2](\1)',
        content
    )
    content = re.sub(
        r'<img\s+[^>]*src=["\']([^"\']+)["\'][^>]*/?>',
        r'![](\1)',
        content
    )
    
    # Headings
    content = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n# \1\n', content, flags=re.DOTALL)
    content = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', content, flags=re.DOTALL)
    content = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', content, flags=re.DOTALL)
    content = re.sub(r'<h4[^>]*>(.*?)</h4>', r'\n#### \1\n', content, flags=re.DOTALL)
    content = re.sub(r'<h5[^>]*>(.*?)</h5>', r'\n##### \1\n', content, flags=re.DOTALL)
    
    # Simple blockquotes (without class - those are protected)
    content = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', r'\n> \1\n', content, flags=re.DOTALL)
    
    # Code blocks
    content = re.sub(r'<pre[^>]*>(.*?)</pre>', r'\n```\n\1\n```\n', content, flags=re.DOTALL)
    content = re.sub(r'<code>(.*?)</code>', r'`\1`', content, flags=re.DOTALL)
    
    # Lists - be careful with nested content
    # First handle list items
    content = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', content, flags=re.DOTALL)
    # Then remove list containers
    content = re.sub(r'</?ul[^>]*>', '\n', content)
    content = re.sub(r'</?ol[^>]*>', '\n', content)
    
    # Paragraphs and line breaks
    content = re.sub(r'<p[^>]*>', '\n', content)
    content = re.sub(r'</p>', '\n\n', content)
    content = re.sub(r'<br\s*/?>', '\n', content)
    
    # Remove remaining simple HTML tags
    # Be conservative - only remove common formatting tags
    simple_tags = ['sup', 'sub', 'small', 'span', 'font', 'center', 'strike', 's', 'u']
    for tag in simple_tags:
        content = re.sub(f'<{tag}[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(f'</{tag}>', '', content, flags=re.IGNORECASE)
    
    # Decode HTML entities
    content = html_lib.unescape(content)
    
    # Clean up excessive whitespace
    content = re.sub(r'\n\n\n+', '\n\n', content)
    content = content.strip()
    
    # STEP 3: Restore protected elements
    for placeholder, original_html in protected_elements.items():
        content = content.replace(placeholder, original_html)
    
    return content

def format_comment_html(comment_data):
    """Format a single comment as HTML"""
    author = html_lib.escape(comment_data['author'])
    date = comment_data['date']
    content = html_lib.escape(comment_data['content'])
    
    html = f'''<div class="comment">
  <div class="comment-meta">
    <strong>{author}</strong> • <time>{date}</time>
  </div>
  <div class="comment-content">
    {content}
  </div>
</div>
'''
    return html

def extract_seo_description(item):
    """Extract SEO description from _aioseo_description"""
    for meta in item.findall('wp:postmeta', NS):
        key = meta.find('wp:meta_key', NS)
        if key is not None and key.text == '_aioseo_description':
            value = meta.find('wp:meta_value', NS)
            if value is not None and value.text:
                return value.text.strip()
    return ""

def convert_post(item, output_dir, include_comments=True, attachments_map=None, use_local_images=False):
    """Convert a single WordPress post to AstroWind markdown"""
    
    # Extract basic fields
    title = item.find('title').text or "Untitled"
    link = item.find('link').text
    pub_date = item.find('wp:post_date', NS).text
    status = item.find('wp:status', NS).text
    post_name = item.find('wp:post_name', NS).text
    
    # Skip drafts and non-published posts
    if status != 'publish':
        return None
    
    # Parse date - AstroWind wants YYYY-MM-DD format
    try:
        date_obj = datetime.strptime(pub_date, '%Y-%m-%d %H:%M:%S')
        date_str = date_obj.strftime('%Y-%m-%d')
        year = date_obj.year
    except:
        date_str = pub_date.split()[0]
        year = int(date_str.split('-')[0])
    
    # Extract categories and tags
    categories = [cat.text for cat in item.findall('category[@domain="category"]') if cat.text]
    tags = [tag.text for tag in item.findall('category[@domain="post_tag"]') if tag.text]
    
    # Get SEO description (for excerpt)
    seo_description = extract_seo_description(item)
    
    # Get featured image
    featured_image = None
    if attachments_map:
        featured_image = extract_featured_image(item, attachments_map)
        # Convert featured image URL to mikeroberto.com/images/ format
        if featured_image:
            # Strip WordPress dimensions if present
            featured_image = re.sub(r'-\d+x\d+(\.[a-zA-Z]+)$', r'\1', featured_image)
            # Extract just the filename
            filename = featured_image.split('/')[-1]
            # Use mikeroberto.com/images/ URL (works on WordPress now, Cloudflare later)
            featured_image = f'https://www.mikeroberto.com/images/{filename}'
    
    # Extract content
    content_elem = item.find('content:encoded', NS)
    html_content = content_elem.text if content_elem is not None else ""
    
    # Convert captions FIRST (before any other processing)
    html_content = convert_wordpress_captions(html_content)
    
    # Convert HTML to markdown (with protection for styled elements)
    markdown_content = clean_html_to_markdown(html_content, use_local_images)
    
    # Extract comments
    comments = []
    if include_comments:
        for comment in item.findall('wp:comment', NS):
            comment_status = comment.find('wp:comment_approved', NS)
            if comment_status is not None and comment_status.text == '1':
                author = comment.find('wp:comment_author', NS).text or "Anonymous"
                date = comment.find('wp:comment_date', NS).text
                content = comment.find('wp:comment_content', NS).text or ""
                
                comments.append({
                    'author': author,
                    'date': date,
                    'content': content
                })
    
    # Build frontmatter
    frontmatter = f"""---
publishDate: {date_str}
title: "{title.replace('"', '\\"')}"
"""
    
    if seo_description:
        frontmatter += f'excerpt: "{seo_description.replace('"', '\\"')}"\n'
    
    if featured_image:
        frontmatter += f'image: "{featured_image}"\n'
    
    if categories:
        # AstroWind uses singular 'category' - take first one
        frontmatter += f'category: "{categories[0].replace('"', '\\"')}"\n'
    
    if tags:
        frontmatter += 'tags:\n'
        for tag in tags:
            frontmatter += f'  - "{tag.replace('"', '\\"')}"\n'
    
    frontmatter += 'author: "Mike Roberto"\n'
    frontmatter += f'wpSlug: "{post_name}"\n'
    frontmatter += f'wpYear: {year}\n'
    
    if comments:
        frontmatter += f'comments_count: {len(comments)}\n'
    
    frontmatter += "---\n"
    
    # Build full markdown
    full_content = frontmatter + "\n" + markdown_content
    
    # Add archived comments if present
    if comments:
        full_content += "\n\n---\n\n## Archived Comments\n\n"
        full_content += '<div class="archived-comments">\n'
        for comment in comments:
            full_content += format_comment_html(comment)
        full_content += '</div>\n'
    
    # Determine output path (year/slug.md)
    year_dir = Path(output_dir) / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = year_dir / f"{post_name}.md"
    
    # Write file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_content)
    
    return {
        'title': title,
        'slug': post_name,
        'year': year,
        'date': date_str,
        'categories': categories,
        'tags': tags,
        'comments': len(comments),
        'file': str(output_file),
        'featured_image': featured_image,
        'has_seo_description': bool(seo_description)
    }

def main():
    parser = argparse.ArgumentParser(
        description='Convert WordPress XML export to AstroWind markdown files'
    )
    parser.add_argument('xml_file', help='WordPress XML export file')
    parser.add_argument('--output-dir', default='src/data/post',
                       help='Output directory for markdown files (default: src/data/post)')
    parser.add_argument('--no-comments', action='store_true',
                       help='Skip comment archival')
    parser.add_argument('--local-images', action='store_true',
                       help='Convert WordPress image URLs to local /images/ paths')
    parser.add_argument('--report', help='Output JSON report file')
    
    args = parser.parse_args()
    
    if args.local_images:
        print("✓ Converting WordPress image URLs to local /images/ paths\n")
    
    print(f"Parsing {args.xml_file}...")
    tree = ET.parse(args.xml_file)
    root = tree.getroot()
    
    # Build attachments map first
    attachments_map = build_attachments_map(root)
    
    # Find all posts
    items = root.findall('.//item')
    print(f"\nConverting {len(items)} items...")
    
    results = []
    converted = 0
    skipped = 0
    
    for idx, item in enumerate(items, 1):
        result = convert_post(
            item, 
            args.output_dir,
            include_comments=not args.no_comments,
            attachments_map=attachments_map,
            use_local_images=args.local_images
        )
        
        if result:
            converted += 1
            results.append(result)
            print(f"  [{idx}/{len(items)}] Converted: {result['title']}")
        else:
            skipped += 1
    
    print(f"\n✓ Conversion complete!")
    print(f"  Converted: {converted} posts")
    print(f"  Skipped: {skipped} (drafts/unpublished)")
    print(f"  Output: {args.output_dir}")
    
    # Generate report if requested
    if args.report:
        report = {
            'total_items': len(items),
            'converted': converted,
            'skipped': skipped,
            'posts': results,
            'generated': datetime.now().isoformat()
        }
        
        with open(args.report, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"  Report: {args.report}")
    
    print("\nNext steps:")
    print("1. Update src/content/config.ts to use pattern: ['**/*.md', '**/*.mdx']")
    print("2. Run: npm run dev")
    print("3. Check your posts at http://localhost:4321")

if __name__ == '__main__':
    main()
