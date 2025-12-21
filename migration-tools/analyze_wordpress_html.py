#!/usr/bin/env python3
"""
Analyze WordPress XML to identify HTML elements that should be preserved
"""

import xml.etree.ElementTree as ET
import re
from collections import Counter
from html.parser import HTMLParser

NS = {
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'wp': 'http://wordpress.org/export/1.2/',
}

class HTMLTagExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.tag_with_attrs = []
        
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if attrs:
            # Record tags that have important attributes (style, class, id)
            important_attrs = {k: v for k, v in attrs if k in ['style', 'class', 'id']}
            if important_attrs:
                self.tag_with_attrs.append((tag, dict(important_attrs)))

def analyze_wordpress_xml(xml_file):
    """Analyze what HTML elements are used in WordPress content"""
    
    print(f"Analyzing {xml_file}...\n")
    
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    all_tags = []
    tags_with_attrs = []
    
    # Analyze all posts
    for item in root.findall('.//item'):
        post_type = item.find('wp:post_type', NS)
        if post_type is not None and post_type.text == 'post':
            status = item.find('wp:status', NS)
            if status is not None and status.text == 'publish':
                # Get content
                content_elem = item.find('content:encoded', NS)
                if content_elem is not None and content_elem.text:
                    parser = HTMLTagExtractor()
                    try:
                        parser.feed(content_elem.text)
                        all_tags.extend(parser.tags)
                        tags_with_attrs.extend(parser.tag_with_attrs)
                    except:
                        pass
    
    # Count tag occurrences
    tag_counts = Counter(all_tags)
    
    print("=" * 70)
    print("HTML TAGS FOUND IN WORDPRESS CONTENT")
    print("=" * 70)
    print(f"\nTotal tags: {len(all_tags)}")
    print(f"\nMost common tags:\n")
    
    for tag, count in tag_counts.most_common(30):
        print(f"  {tag:20s} - {count:5d} occurrences")
    
    # Analyze tags with special attributes
    print(f"\n\n" + "=" * 70)
    print("TAGS WITH STYLE/CLASS/ID ATTRIBUTES")
    print("=" * 70)
    
    tags_with_style = [t for t, attrs in tags_with_attrs if 'style' in attrs]
    tags_with_class = [t for t, attrs in tags_with_attrs if 'class' in attrs]
    
    print(f"\nTags with inline styles: {len(tags_with_style)}")
    style_counts = Counter(tags_with_style)
    for tag, count in style_counts.most_common(10):
        print(f"  {tag:20s} - {count} occurrences")
    
    print(f"\nTags with classes: {len(tags_with_class)}")
    class_counts = Counter(tags_with_class)
    for tag, count in class_counts.most_common(10):
        print(f"  {tag:20s} - {count} occurrences")
    
    # Sample some actual styled divs
    print(f"\n\n" + "=" * 70)
    print("SAMPLE DIVS WITH INLINE STYLES")
    print("=" * 70)
    
    sample_count = 0
    for item in root.findall('.//item'):
        post_type = item.find('wp:post_type', NS)
        if post_type is not None and post_type.text == 'post':
            status = item.find('wp:status', NS)
            if status is not None and status.text == 'publish':
                content_elem = item.find('content:encoded', NS)
                if content_elem is not None and content_elem.text:
                    # Find divs with style attributes
                    div_matches = re.findall(r'<div[^>]*style=[^>]*>.*?</div>', 
                                            content_elem.text, re.DOTALL)
                    for div_html in div_matches[:3]:  # Show first 3
                        if sample_count < 5:  # Limit total samples
                            title = item.find('title').text
                            print(f"\nPost: {title}")
                            print(f"HTML: {div_html[:200]}..." if len(div_html) > 200 else div_html)
                            sample_count += 1
    
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_wordpress_html.py <wordpress-export.xml>")
        sys.exit(1)
    
    analyze_wordpress_xml(sys.argv[1])
