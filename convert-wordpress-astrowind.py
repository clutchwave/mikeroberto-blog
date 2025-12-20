#!/usr/bin/env python3
"""
WordPress to AstroWind Migration Script
Converts WordPress XML export to AstroWind-compatible markdown files

Version: 2.1 - Fixed featured image extraction bug
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

def clean_html_to_markdown(html_content):
    """Convert WordPress HTML to cleaner markdown"""
    if not html_content:
        return ""
    
    content = html_content
    
    # FIRST: Protect figure tags from conversion by temporarily replacing them
    # We'll restore them at the end, keeping them as HTML
    figure_placeholders = {}
    figure_counter = 0
    
    def save_figure(match):
        nonlocal figure_counter
        placeholder = f"___FIGURE_PLACEHOLDER_{figure_counter}___"
        figure_placeholders[placeholder] = match.group(0)
        figure_counter += 1
        return placeholder
    
    # Save all figure tags (they're already properly formatted from convert_wordpress_captions)
    content = re.sub(r'<figure[^>]*>.*?</figure>', save_figure, content, flags=re.DOTALL)
    
    # Convert common HTML to markdown
    content = re.sub(r'<strong>(.*?)</strong>', r'**\1**', content)
    content = re.sub(r'<b>(.*?)</b>', r'**\1**', content)
    content = re.sub(r'<em>(.*?)</em>', r'*\1*', content)
    content = re.sub(r'<i>(.*?)</i>', r'*\1*', content)
    
    # Handle links
    content = re.sub(r'<a\s+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r'[\2](\1)', content)
    
    # Handle images - keep track for later processing
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
    
    # Handle lists
    content = re.sub(r'<ul[^>]*>', '\n', content)
    content = re.sub(r'</ul>', '\n', content)
    content = re.sub(r'<ol[^>]*>', '\n', content)
    content = re.sub(r'</ol>', '\n', content)
    content = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', content)
    
    # Handle paragraphs
    content = re.sub(r'<p[^>]*>', '\n', content)
    content = re.sub(r'</p>', '\n\n', content)
    content = re.sub(r'<br\s*/?>', '\n', content)
    
    # Handle headings
    content = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n# \1\n', content)
    content = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', content)
    content = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', content)
    content = re.sub(r'<h4[^>]*>(.*?)</h4>', r'\n#### \1\n', content)
    
    # Handle blockquotes
    content = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', r'\n> \1\n', content, flags=re.DOTALL)
    
    # Handle code blocks
    content = re.sub(r'<pre[^>]*>(.*?)</pre>', r'\n```\n\1\n```\n', content, flags=re.DOTALL)
    content = re.sub(r'<code>(.*?)</code>', r'`\1`', content)
    
    # Remove remaining HTML tags
    content = re.sub(r'<[^>]+>', '', content)
    
    # Decode HTML entities
    content = html_lib.unescape(content)
    
    # Clean up excessive whitespace
    content = re.sub(r'\n\n\n+', '\n\n', content)
    content = content.strip()
    
    # Restore figure tags as HTML (they stay as HTML in the markdown file)
    for placeholder, figure_html in figure_placeholders.items():
        content = content.replace(placeholder, figure_html)
    
    return content

def extract_images(content):
    """Extract image URLs from content"""
    img_pattern = r'!\[([^\]]*)\]\(([^\)]+)\)'
    images = re.findall(img_pattern, content)
    return [img[1] for img in images]

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

def build_attachment_lookup(root):
    """Build a lookup table of attachment IDs to URLs"""
    attachments = {}
    debug_first_few = True
    count = 0
    
    for item in root.findall('.//item'):
        post_type = item.find('wp:post_type', NS)
        if post_type is not None and post_type.text == 'attachment':
            post_id_elem = item.find('wp:post_id', NS)
            if post_id_elem is None:
                continue
                
            post_id = post_id_elem.text
            
            # Try wp:attachment_url first (most reliable)
            attachment_url = item.find('wp:attachment_url', NS)
            if attachment_url is not None and attachment_url.text:
                attachments[post_id] = attachment_url.text
                # Debug: show first few attachments
                if debug_first_few and count < 3:
                    print(f"  [DEBUG] Attachment {post_id}: {attachment_url.text[:60]}...")
                count += 1
            else:
                # Fall back to guid
                guid = item.find('guid')
                if guid is not None and guid.text:
                    attachments[post_id] = guid.text
                    if debug_first_few and count < 3:
                        print(f"  [DEBUG] Attachment {post_id} (from guid): {guid.text[:60]}...")
                    count += 1
    
    return attachments

def extract_post_meta(item):
    """Extract post meta fields into a dictionary"""
    meta = {}
    
    for postmeta in item.findall('wp:postmeta', NS):
        key_elem = postmeta.find('wp:meta_key', NS)
        value_elem = postmeta.find('wp:meta_value', NS)
        
        if key_elem is not None and value_elem is not None:
            key = key_elem.text
            value = value_elem.text
            if key and value:
                meta[key] = value
    
    return meta

def generate_excerpt_from_content(content, max_length=160):
    """Generate excerpt from post content"""
    if not content:
        return ""
    
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', '', content)
    
    # Decode HTML entities
    text = html_lib.unescape(text)
    
    # Clean up whitespace
    text = ' '.join(text.split())
    
    # Truncate to max_length at word boundary
    if len(text) <= max_length:
        return text
    
    # Find last space before max_length
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > 0:
        truncated = truncated[:last_space]
    
    return truncated + '...'

def convert_post(item, output_dir, attachment_lookup, include_comments=True):
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
        year = date_str.split('-')[0]
    
    # Extract categories and tags
    categories = [cat.text for cat in item.findall('category[@domain="category"]') if cat.text]
    tags = [tag.text for tag in item.findall('category[@domain="post_tag"]') if tag.text]
    
    # Extract post meta (featured images, SEO data, etc.)
    post_meta = extract_post_meta(item)
    
    # Get featured image from _thumbnail_id
    featured_image = None
    if '_thumbnail_id' in post_meta:
        thumbnail_id = post_meta['_thumbnail_id']
        print(f"    [DEBUG] Post '{post_name}' has _thumbnail_id: {thumbnail_id}")
        if thumbnail_id in attachment_lookup:
            featured_image = attachment_lookup[thumbnail_id]
            print(f"    [DEBUG] Found featured image: {featured_image[:60]}...")
        else:
            print(f"    [DEBUG] Attachment ID {thumbnail_id} not found in lookup table!")
            print(f"    [DEBUG] Lookup has {len(attachment_lookup)} attachments")
            # Show a few IDs from lookup for debugging
            sample_ids = list(attachment_lookup.keys())[:5]
            print(f"    [DEBUG] Sample attachment IDs: {sample_ids}")
    
    # Extract content
    content_elem = item.find('content:encoded', NS)
    content = content_elem.text if content_elem is not None else ""
    
    # Convert WordPress caption shortcodes to proper HTML first
    content = convert_wordpress_captions(content)
    
    # Extract excerpt with smart fallback
    # Priority: 1) AIOSEO description, 2) WordPress excerpt, 3) Auto-generate from content
    excerpt = ""
    
    # Check AIOSEO description first (best for SEO!)
    if '_aioseo_description' in post_meta and post_meta['_aioseo_description']:
        excerpt = post_meta['_aioseo_description'].strip()
    
    # Fall back to WordPress excerpt
    if not excerpt:
        excerpt_elem = item.find('excerpt:encoded', NS)
        if excerpt_elem is not None and excerpt_elem.text:
            excerpt = excerpt_elem.text.strip()
    
    # Fall back to auto-generated from content
    if not excerpt and content:
        excerpt = generate_excerpt_from_content(content, max_length=160)
    
    # Convert content to markdown
    markdown_content = clean_html_to_markdown(content)
    
    # NOTE: featured_image is already extracted above from _thumbnail_id
    # (Removed duplicate call to extract_featured_image() that was overwriting it)
    
    # Extract images from content
    images = extract_images(markdown_content)
    
    # Handle comments
    comments = []
    comment_elems = item.findall('wp:comment', NS)
    for comment in comment_elems:
        author = comment.find('wp:comment_author', NS).text or "Anonymous"
        date = comment.find('wp:comment_date', NS).text
        content = comment.find('wp:comment_content', NS).text or ""
        approved = comment.find('wp:comment_approved', NS).text
        
        if approved == '1':  # Only include approved comments
            comments.append({
                'author': author,
                'date': date,
                'content': content
            })
    
    # Create AstroWind-compatible frontmatter
    frontmatter = {
        'publishDate': date_str,  # AstroWind uses publishDate (will be parsed as Date)
        'title': title,
        'excerpt': excerpt,  # Now always populated (from excerpt or content)
        'category': categories[0] if categories else '',  # AstroWind uses singular 'category'
        'tags': tags,
        'author': 'Mike Roberto',
        # Optional fields
        'wpSlug': post_name,  # Preserve WordPress slug for reference
        'wpYear': year,  # Preserve year for reference
        'comments_count': len(comments)
    }
    
    # Add featured image if available
    if featured_image:
        frontmatter['image'] = featured_image
    
    # Add metadata for SEO (canonical URL)
    frontmatter['metadata'] = {
        'canonical': f'https://www.mikeroberto.com/{year}/{post_name}'
    }
    
    # Debug: Show what's in frontmatter for class-of-2000
    if post_name == 'class-of-2000':
        print(f"    [DEBUG] Frontmatter dict keys: {list(frontmatter.keys())}")
        if 'image' in frontmatter:
            print(f"    [DEBUG] frontmatter['image'] = {frontmatter['image'][:80] if frontmatter['image'] else 'EMPTY'}")
        else:
            print(f"    [DEBUG] 'image' key NOT in frontmatter dict!")
    
    # Build the markdown file with proper YAML formatting
    md_lines = ['---']
    for key, value in frontmatter.items():
        if isinstance(value, dict):
            # Handle nested dicts (like metadata)
            md_lines.append(f'{key}:')
            for subkey, subvalue in value.items():
                if isinstance(subvalue, str):
                    safe_value = subvalue.replace('"', '\\"')
                    md_lines.append(f'  {subkey}: "{safe_value}"')
                else:
                    md_lines.append(f'  {subkey}: {subvalue}')
        elif isinstance(value, list):
            if value:
                md_lines.append(f'{key}:')
                for item in value:
                    safe_item = str(item).replace('"', '\\"')
                    md_lines.append(f'  - "{safe_item}"')
        elif isinstance(value, str):
            if value:  # Only add non-empty strings
                # Don't quote publishDate - it needs to be parsed as a date type
                if key == 'publishDate':
                    md_lines.append(f'{key}: {value}')
                else:
                    safe_value = value.replace('"', '\\"')
                    md_lines.append(f'{key}: "{safe_value}"')
        elif isinstance(value, (int, float)):
            md_lines.append(f'{key}: {value}')
    md_lines.append('---')
    md_lines.append('')
    md_lines.append(markdown_content)
    
    # Add archived comments if requested
    if include_comments and comments:
        md_lines.append('')
        md_lines.append('---')
        md_lines.append('')
        md_lines.append(f'## Archived Comments ({len(comments)})')
        md_lines.append('')
        md_lines.append('<div class="archived-comments">')
        for comment in comments:
            md_lines.append(format_comment_html(comment))
        md_lines.append('</div>')
    
    # Create filename with year subdirectory to preserve WordPress /YYYY/slug URLs
    # AstroWind generates URLs from file path, so:
    #   src/data/post/2019/high-protein-kidney.md → /2019/high-protein-kidney
    # New posts without year subdirectory will just be /slug
    year_dir = output_dir / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{post_name}.md"
    filepath = year_dir / filename
    
    # Write file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))
    
    return {
        'filename': filename,
        'title': title,
        'date': date_str,
        'slug': post_name,
        'year': year,
        'categories': categories,
        'tags': tags,
        'images': images,
        'featured_image': featured_image if featured_image else '',
        'excerpt': excerpt if excerpt else '',
        'comments': len(comments),
        'original_url': link
    }

def main():
    parser = argparse.ArgumentParser(description='Convert WordPress XML to AstroWind markdown')
    parser.add_argument('input_xml', help='WordPress XML export file')
    parser.add_argument('--output-dir', default='src/data/post', help='Output directory for markdown files')
    parser.add_argument('--no-comments', action='store_true', help='Exclude archived comments')
    parser.add_argument('--report', default='migration-report.json', help='Migration report file')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Parse XML
    print(f"Parsing {args.input_xml}...")
    tree = ET.parse(args.input_xml)
    root = tree.getroot()
    
    # Build attachment lookup table for featured images
    print("Building attachment lookup table...")
    attachment_lookup = build_attachment_lookup(root)
    print(f"  Found {len(attachment_lookup)} attachments")
    
    # Debug: Check if specific attachment 713 is in lookup
    if '713' in attachment_lookup:
        print(f"  [DEBUG] Attachment 713 found: {attachment_lookup['713']}")
    else:
        print(f"  [DEBUG] Attachment 713 NOT found in lookup!")
        # Check if it exists as different type
        all_ids = [item.find('wp:post_id', NS).text for item in root.findall('.//item') 
                   if item.find('wp:post_id', NS) is not None]
        if '713' in all_ids:
            print(f"  [DEBUG] But post_id 713 exists in XML!")
            # Find it and check its type
            for item in root.findall('.//item'):
                pid = item.find('wp:post_id', NS)
                if pid is not None and pid.text == '713':
                    ptype = item.find('wp:post_type', NS)
                    print(f"  [DEBUG] Post 713 has type: {ptype.text if ptype is not None else 'None'}")
                    break
    
    # Get all posts
    items = root.findall('.//item')
    posts_data = []
    
    print(f"\nConverting {len(items)} items...")
    for i, item in enumerate(items, 1):
        post_type = item.find('wp:post_type', NS)
        if post_type is not None and post_type.text == 'post':
            result = convert_post(item, output_dir, attachment_lookup, include_comments=not args.no_comments)
            if result:
                posts_data.append(result)
                print(f"  [{i}/{len(items)}] Converted: {result['title']}")
    
    # Generate report
    report = {
        'conversion_date': datetime.now().isoformat(),
        'total_posts': len(posts_data),
        'posts_with_comments': sum(1 for p in posts_data if p['comments'] > 0),
        'total_comments': sum(p['comments'] for p in posts_data),
        'posts_with_featured_images': sum(1 for p in posts_data if p.get('featured_image')),
        'categories': sorted(list(set(cat for p in posts_data for cat in p['categories']))),
        'tags': sorted(list(set(tag for p in posts_data for tag in p['tags']))),
        'all_images': sorted(list(set(img for p in posts_data for img in p['images']))),
        'posts': posts_data
    }
    
    # Save report
    with open(args.report, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✓ Conversion complete!")
    print(f"  Posts converted: {len(posts_data)}")
    print(f"  Posts with comments: {report['posts_with_comments']}")
    print(f"  Total comments: {report['total_comments']}")
    print(f"  Posts with featured images: {report['posts_with_featured_images']}")
    print(f"  Categories: {len(report['categories'])}")
    print(f"  Tags: {len(report['tags'])}")
    print(f"  Images found: {len(report['all_images'])}")
    
    print(f"\nReport saved to: {args.report}")
    print(f"\nURL Structure:")
    print(f"  Old posts: /YYYY/slug (preserved via subdirectories: YYYY/slug.md)")
    print(f"  New posts: /slug (create as: slug.md)")
    print(f"\nContent enhancements:")
    print(f"  - WordPress caption shortcodes converted to <figure> tags with alignment classes")
    print(f"  - Excerpts auto-generated from content when not provided (first ~160 chars)")
    print(f"  - Canonical URLs added to metadata for SEO")
    print(f"  - Featured images extracted from _thumbnail_id")
    print(f"\nNext steps:")
    print(f"  1. Review posts in: {args.output_dir}")
    print(f"  2. Add wordpress-caption-styles.css for image alignment")
    print(f"  3. Test build: npm run build")
    print(f"  4. Run convert-redirects-astrowind.py for WordPress Redirection plugin redirects")

if __name__ == '__main__':
    main()
