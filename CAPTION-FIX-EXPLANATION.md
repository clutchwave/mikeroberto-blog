# Caption Fix Explanation

## The Problem

WordPress caption shortcodes were being converted to `<figure>` tags, but then those figures were being converted to markdown, breaking the caption structure:

**What was happening:**
```markdown
[![Image](url)](link)
  Caption text here
```
Caption appears as a separate paragraph, not associated with the image.

## The Solution

The converter now **protects figure tags** from markdown conversion. They stay as HTML in the markdown file.

**What happens now:**
```markdown
<figure class="aligncenter">
  <a href="full-size-url"><img src="thumbnail-url" alt="Alt text"></a>
  <figcaption>The Enemy of Truth is not necessarily the lie, but the <em>myth</em>. Today, we fight to destroy one such myth.</figcaption>
</figure>
```

## How It Works

1. WordPress `[caption]` shortcodes → `<figure>` tags (with alignment classes)
2. Figure tags are temporarily protected with placeholders
3. All other HTML gets converted to markdown
4. Figure tags are restored as HTML

## Why HTML in Markdown?

Astro/MDX handles HTML perfectly fine! Keeping captions as HTML means:
- ✅ Captions stay properly associated with images
- ✅ Alignment classes preserved (`aligncenter`, `alignleft`, `alignright`)
- ✅ Links around images preserved
- ✅ Caption formatting (italics, bold, etc.) preserved

## Re-Running the Conversion

To pick up this fix:

```bash
cd ~/perl/astro/mikeroberto-astro

# Delete existing posts
rm -rf src/data/post/*/

# Re-run with caption fix
python3 convert-wordpress-astrowind.py \
    migration-tools/mikeroberto-wordpress-export-EVERYTHING-for-comments-2025-12-18.xml \
    --output-dir src/data/post

# Test
npm run dev
```

Now captions should display properly under their images!

## What You'll See

**In the markdown file:**
```html
<figure class="aligncenter">
  <a href="..."><img src="..." alt="..."></a>
  <figcaption>Caption text with <em>formatting</em></figcaption>
</figure>
```

**On the rendered page:**
- Image centered (or aligned left/right)
- Caption text directly below image
- Caption styled with CSS (gray, italic, smaller text)
- All formatting preserved

Make sure you've added the `wordpress-caption-styles.css` to your theme for proper styling!
