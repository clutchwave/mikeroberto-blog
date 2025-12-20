#!/usr/bin/env python3
"""
WordPress to AstroWind Migration Script
Converts WordPress XML export to AstroWind-compatible markdown files
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

def clean_html_to_markdown(html_content):
    """Convert WordPress HTML to cleaner markdown"""
    if not html_content:
        return ""
    
    content = html_content
    
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

def convert_post(item, output_dir, include_comments=True):
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
    
    # Extract content
    content_elem = item.find('content:encoded', NS)
    content = content_elem.text if content_elem is not None else ""
    
    # Extract excerpt
    excerpt_elem = item.find('excerpt:encoded', NS)
    excerpt = excerpt_elem.text if excerpt_elem is not None and excerpt_elem.text else ""
    excerpt = excerpt.strip() if excerpt else ""
    
    # Convert content to markdown
    markdown_content = clean_html_to_markdown(content)
    
    # Extract images
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
        'excerpt': excerpt[:160] if excerpt else '',  # AstroWind uses 'excerpt' not 'description'
        'category': categories[0] if categories else '',  # AstroWind uses singular 'category'
        'tags': tags,
        'author': 'Mike Roberto',  # You can customize this
        # Custom fields for WordPress migration
        'wpSlug': post_name,  # Preserve WordPress slug for redirects
        'wpYear': year,  # Preserve year for redirects
        'comments_count': len(comments)
    }
    
    # Build the markdown file with proper YAML formatting
    md_lines = ['---']
    for key, value in frontmatter.items():
        if isinstance(value, list):
            if value:
                md_lines.append(f'{key}:')
                for item in value:
                    safe_item = str(item).replace('"', '\\"')
                    md_lines.append(f'  - "{safe_item}"')
        elif isinstance(value, str):
            if value:  # Only add non-empty strings
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
    
    # Create filename - Include year to preserve WordPress /YYYY/slug URLs
    # AstroWind generates URLs from filenames, so:
    #   2019-high-protein-kidney.md → /2019/high-protein-kidney
    # New posts without year prefix will just be /slug
    filename = f"{year}-{post_name}.md"
    filepath = output_dir / filename
    
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
    
    # Get all posts
    items = root.findall('.//item')
    posts_data = []
    
    print(f"\nConverting {len(items)} items...")
    for i, item in enumerate(items, 1):
        post_type = item.find('wp:post_type', NS)
        if post_type is not None and post_type.text == 'post':
            result = convert_post(item, output_dir, include_comments=not args.no_comments)
            if result:
                posts_data.append(result)
                print(f"  [{i}/{len(items)}] Converted: {result['title']}")
    
    # Generate report
    report = {
        'conversion_date': datetime.now().isoformat(),
        'total_posts': len(posts_data),
        'posts_with_comments': sum(1 for p in posts_data if p['comments'] > 0),
        'total_comments': sum(p['comments'] for p in posts_data),
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
    print(f"  Categories: {len(report['categories'])}")
    print(f"  Tags: {len(report['tags'])}")
    print(f"  Images found: {len(report['all_images'])}")
    print(f"\nReport saved to: {args.report}")
    print(f"\nURL Structure:")
    print(f"  Old posts: /YYYY/slug (preserved via filenames: YYYY-slug.md)")
    print(f"  New posts: /slug (create as: slug.md)")
    print(f"\nNext steps:")
    print(f"  1. Review posts in: {args.output_dir}")
    print(f"  2. Test build: npm run build")
    print(f"  3. Run convert-redirects-astrowind.py for WordPress Redirection plugin redirects")

if __name__ == '__main__':
    main()
