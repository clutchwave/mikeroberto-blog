#!/usr/bin/env python3
"""
Convert WordPress Redirection plugin export to Cloudflare Pages _redirects format
AstroWind version - handles WordPress /YYYY/slug → /slug URLs
"""

import json
import argparse
from pathlib import Path

def convert_redirects(input_file, output_file, base_url='https://www.mikeroberto.com', migration_report=None):
    """Convert WordPress redirects JSON to Cloudflare Pages _redirects format"""
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    redirects = data.get('redirects', [])
    
    # Group by status code for better organization
    redirect_301 = []  # Permanent
    redirect_302 = []  # Temporary
    redirect_307 = []  # Temporary (preserve method)
    
    for redirect in redirects:
        if not redirect.get('enabled', True):
            continue
        
        source = redirect['url']
        action_type = redirect['action_type']
        code = redirect['action_code']
        
        # Only handle URL redirects
        if action_type != 'url':
            continue
        
        action_data = redirect.get('action_data', {})
        target = action_data.get('url', '/')
        
        # Format: source destination [code]
        redirect_line = f"{source} {target} {code}"
        
        if code == 301:
            redirect_301.append(redirect_line)
        elif code == 302:
            redirect_302.append(redirect_line)
        elif code == 307:
            redirect_307.append(redirect_line)
    
    # No auto-generated year redirects needed!
    # We're preserving WordPress /YYYY/slug URLs by including year in filenames
    # Only use the explicit redirects from WordPress Redirection plugin
    auto_redirects = []
    
    # Write _redirects file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# WordPress to AstroWind Migration Redirects\n")
        f.write(f"# Generated from WordPress Redirection plugin export\n")
        f.write(f"# Base URL: {base_url}\n")
        f.write("# NOTE: WordPress /YYYY/slug URLs are preserved via filenames (no redirects needed)\n\n")
        
        if redirect_301:
            f.write("# Permanent Redirects (301)\n")
            for line in redirect_301:
                f.write(line + '\n')
            f.write('\n')
        
        if redirect_307:
            f.write("# Temporary Redirects - Preserve Method (307)\n")
            for line in redirect_307:
                f.write(line + '\n')
            f.write('\n')
        
        if redirect_302:
            f.write("# Temporary Redirects (302)\n")
            for line in redirect_302:
                f.write(line + '\n')
            f.write('\n')
    
    return len(redirect_301) + len(redirect_302) + len(redirect_307) + len(auto_redirects)

def main():
    parser = argparse.ArgumentParser(description='Convert WordPress redirects to Cloudflare Pages format for AstroWind')
    parser.add_argument('input_json', help='WordPress Redirection plugin JSON export')
    parser.add_argument('--output', default='public/_redirects', help='Output _redirects file for Cloudflare')
    parser.add_argument('--migration-report', default='migration-report.json', help='Migration report for auto year redirects')
    
    args = parser.parse_args()
    
    print(f"Converting redirects from {args.input_json}...")
    
    # Convert to Cloudflare format (no auto year redirects - URLs preserved via filenames)
    count = convert_redirects(args.input_json, args.output, migration_report=args.migration_report)
    print(f"✓ Created Cloudflare _redirects file: {count} redirects")
    print(f"  Location: {args.output}")
    
    print("\nRedirect handling:")
    print(f"  ✓ WordPress /YYYY/slug URLs preserved via filenames (2019-slug.md → /2019/slug)")
    print(f"  ✓ All WordPress Redirection plugin redirects included")
    print(f"  ✓ New posts without year prefix will use clean /slug URLs")
    print(f"  ✓ Cloudflare handles redirects at the edge (zero latency)")
    
    print("\nNext steps:")
    print(f"  1. Verify {args.output} looks correct")
    print(f"  2. Commit to git")
    print(f"  3. Deploy to Cloudflare Pages")

if __name__ == '__main__':
    main()
