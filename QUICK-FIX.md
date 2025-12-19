# QUICK FIX: URLs Missing Slash + Caption Shortcodes

## Issues Fixed
1. Posts are at `/2019-high-protein-kidney` instead of `/2019/high-protein-kidney`
2. WordPress `[caption]` shortcodes not converted to proper HTML

## The Cause
- AstroWind generates URLs from **file path**, not filename. We need subdirectories.
- WordPress caption shortcodes need to be converted to `<figure>` tags before markdown processing

## The Fix (4 steps)

### Step 1: Delete incorrectly formatted posts
```bash
cd ~/perl/astro/mikeroberto-astro
rm -rf src/data/post/*.md
```

### Step 2: Update AstroWind content config
Edit `src/content/config.ts`:

**Find this line (~line 49):**
```typescript
loader: glob({ pattern: ['*.md', '*.mdx'], base: 'src/data/post' }),
```

**Change to:**
```typescript
loader: glob({ pattern: ['**/*.md', '**/*.mdx'], base: 'src/data/post' }),
```

Save the file.

### Step 3: Re-run conversion with updated script
```bash
# Download the new convert-wordpress-astrowind.py from Claude
# Then:

python3 convert-wordpress-astrowind.py \
    migration-tools/mikeroberto-wordpress-export-EVERYTHING-for-comments-2025-12-18.xml \
    --output-dir src/data/post \
    --report migration-report.json
```

### Step 4: Test
```bash
npm run dev

# Check directory structure
ls -l src/data/post/
ls -l src/data/post/2019/

# Visit in browser
http://localhost:4321/2019/high-protein-kidney
```

### Step 5: Add caption styling CSS (optional but recommended)

Download `wordpress-caption-styles.css` from Claude and add the CSS to your theme.

**Option 1: Add to global styles**
Copy the CSS into `src/assets/styles/base.css` (or create it if it doesn't exist)

**Option 2: Add to blog post component**
Add a `<style>` tag in your blog post layout (e.g., `src/layouts/BlogPost.astro` or similar)

This will properly style:
- `aligncenter` - Centered images
- `alignleft` - Floated left with text wrap
- `alignright` - Floated right with text wrap
- Responsive behavior on mobile

## What Changed

**URLs - Before:**
```
src/data/post/2019-high-protein-kidney.md → /2019-high-protein-kidney ❌
```

**URLs - After:**
```
src/data/post/2019/high-protein-kidney.md → /2019/high-protein-kidney ✓
```

The year subdirectory creates the `/` in the URL!

**Captions - Before:**
```html
[caption align="aligncenter" width="625"]<img src="..." alt="...">Caption text here[/caption]
```

**Captions - After:**
```html
<figure class="aligncenter">
  <img src="..." alt="...">
  <figcaption>Caption text here</figcaption>
</figure>
```

Now properly styled with CSS classes for alignment!

## For Future Posts

**Clean URL (no year):**
```bash
vim src/data/post/my-article.md  # → /my-article
```

**With year:**
```bash
mkdir -p src/data/post/2025
vim src/data/post/2025/my-article.md  # → /2025/my-article
```
