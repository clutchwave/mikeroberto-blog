# WordPress to AstroWind Migration Guide

Complete step-by-step guide for migrating your WordPress blog to AstroWind.

## What We're Doing

1. Converting 61 WordPress posts to AstroWind markdown format
2. **Preserving WordPress /YYYY/slug URLs** by including year in filenames
3. Preserving 290 comments as archived HTML
4. Creating Cloudflare redirects for WordPress Redirection plugin exports only
5. Handling categories, tags, and images

## Key URL Strategy

**AstroWind generates URLs from filenames:**
- Old post: `2019-high-protein-kidney.md` → `/2019/high-protein-kidney` ✓
- New post: `my-new-article.md` → `/my-new-article` ✓

This means:
- ✅ All WordPress URLs stay exactly the same
- ✅ No redirects needed for migrated posts
- ✅ New posts can use clean `/slug` URLs without year prefix
- ✅ You have full flexibility going forward

## Key Differences: Old Astro vs AstroWind

| Aspect | Old Setup | AstroWind |
|--------|-----------|-----------|
| Directory | `src/content/blog/` | `src/data/post/` |
| Date field | `pubDate` | `publishDate` |
| Description | `description` | `excerpt` |
| Categories | `categories` (array) | `category` (single string) |
| Filenames | `YYYY-MM-DD-slug.md` | `YYYY-slug.md` (for old posts) |
| URL format | `/YYYY/slug` | `/YYYY/slug` (old), `/slug` (new) |
| Slug control | In frontmatter | From filename |

## Prerequisites

You should have:
- Fresh AstroWind clone at `~/perl/astro/mikeroberto-astro`
- Backup at `~/perl/astro/mikeroberto-astro-backup`
- WordPress export XML file
- Redirects JSON file

## Creating New Posts (After Migration)

Once migrated, you have full flexibility for new posts:

**Option 1: Clean URLs (recommended for new posts)**
```bash
cd ~/perl/astro/mikeroberto-astro/src/data/post
vim my-new-article.md  # → URL: /my-new-article
```

**Option 2: With year (if you want consistency with old posts)**
```bash
mkdir -p 2025  # Create year directory if needed
vim 2025/my-new-article.md  # → URL: /2025/my-new-article
```

AstroWind generates URLs from the file path, so you have complete control!

## Step-by-Step Migration

### Step 1: Copy Migration Scripts

```bash
cd ~/perl/astro/mikeroberto-astro

# Download the three files from Claude and save them here:
# - convert-wordpress-astrowind.py
# - convert-redirects-astrowind.py  
# - migrate-to-astrowind.sh (optional automation)

chmod +x *.py *.sh
```

### Step 2: Create Migration Tools Directory

```bash
mkdir -p migration-tools
cd migration-tools
```

### Step 3: Copy WordPress Data Files

```bash
# Copy from your backup
cp ~/perl/astro/mikeroberto-astro-backup/migration-tools/mikeroberto-wordpress-export-EVERYTHING-for-comments-2025-12-18.xml .

cp ~/perl/astro/mikeroberto-astro-backup/migration-tools/redirection-www-mikeroberto-com-december-17-2025.json .
```

### Step 4: Run WordPress Conversion

```bash
cd ~/perl/astro/mikeroberto-astro/migration-tools

python3 ../convert-wordpress-astrowind.py \
    mikeroberto-wordpress-export-EVERYTHING-for-comments-2025-12-18.xml \
    --output-dir ../src/data/post \
    --report migration-report.json
```

**What this does:**
- Creates markdown files organized by year: `src/data/post/2019/high-protein-kidney.md`
- This directory structure creates the `/2019/high-protein-kidney` URL
- Converts frontmatter to AstroWind format:
  - `publishDate: 2019-12-15` (unquoted for date parsing)
  - `category: "Health & Fitness"` (takes first category)
  - `excerpt:` instead of `description:`
- Preserves comments as HTML at bottom of posts
- Generates `migration-report.json` with full inventory

### Step 4.5: Update AstroWind Content Config

**Important:** AstroWind needs to look in subdirectories for your posts.

Edit `src/content/config.ts` and change the glob pattern:

```typescript
// BEFORE:
loader: glob({ pattern: ['*.md', '*.mdx'], base: 'src/data/post' }),

// AFTER:
loader: glob({ pattern: ['**/*.md', '**/*.mdx'], base: 'src/data/post' }),
```

The `**/` makes it search recursively in year subdirectories.

**Expected output:**
```
Parsing mikeroberto-wordpress-export-EVERYTHING-for-comments-2025-12-18.xml...

Converting 1234 items...
  [1/1234] Converted: High Protein Diet and Kidney Function
  [2/1234] Converted: Blood Work Results - July 2024
  ...

✓ Conversion complete!
  Posts converted: 61
  Posts with comments: 50
  Total comments: 290
  Categories: 17
  Tags: 129
  Images found: 239

Report saved to: migration-report.json

URL Structure:
  Old posts: /YYYY/slug (preserved via subdirectories: YYYY/slug.md)
  New posts: /slug (create as: slug.md)

Note: WordPress [caption] shortcodes converted to <figure> tags with alignment classes
```

### Step 5: Generate Redirects

```bash
python3 ../convert-redirects-astrowind.py \
    redirection-www-mikeroberto-com-december-17-2025.json \
    --output ../public/_redirects \
    --migration-report migration-report.json
```

**What this does:**
- Creates `public/_redirects` for Cloudflare Pages
- Includes all your existing WordPress Redirection plugin redirects
- **Does NOT create year-based redirects** (WordPress URLs preserved via filenames)

**Expected output:**
```
Converting redirects from redirection-www-mikeroberto-com-december-17-2025.json...
✓ Created Cloudflare _redirects file: 109 redirects
  Location: ../public/_redirects

Redirect handling:
  ✓ WordPress /YYYY/slug URLs preserved via filenames (2019-slug.md → /2019/slug)
  ✓ All WordPress Redirection plugin redirects included
  ✓ New posts without year prefix will use clean /slug URLs
  ✓ Cloudflare handles redirects at the edge (zero latency)
```

### Step 6: Verify the Migration

```bash
cd ~/perl/astro/mikeroberto-astro

# Check posts were created
ls -l src/data/post/
ls -l src/data/post/2019/ | head -5

# View a sample post
cat src/data/post/2019/high-protein-kidney.md | head -30

# Check redirects
cat public/_redirects | head -20

# Review migration report
cat migration-tools/migration-report.json | jq '.total_posts, .posts_with_comments, .total_comments'
```

**Sample post should look like:**
```markdown
---
publishDate: "2019-12-15"
title: "High Protein Diet and Kidney Function"
excerpt: "Does eating high protein damage your kidneys?"
category: "Health & Fitness"
tags:
  - "nutrition"
  - "protein"
  - "kidneys"
author: "Mike Roberto"
wpSlug: "high-protein-kidney"
wpYear: 2019
comments_count: 12
---

Your content starts here...
```

### Step 7: Test Local Build

```bash
cd ~/perl/astro/mikeroberto-astro

# Install dependencies if needed
npm install

# Start dev server
npm run dev
```

Visit `http://localhost:4321` and check:
- [ ] Homepage loads
- [ ] Blog posts are listed
- [ ] Individual posts load at their WordPress URLs (try `/2019/high-protein-kidney`)
- [ ] Categories/tags work
- [ ] Images display (external URLs should still work)

### Step 8: Handle Images (Optional)

Your posts currently reference WordPress image URLs. They'll work fine, but if you want to migrate them locally:

```bash
cd ~/perl/astro/mikeroberto-astro

# Copy images from your WordPress backup
cp -r ~/path/to/wordpress/wp-content/uploads public/images/

# Then manually update image paths in posts:
# From: https://www.mikeroberto.com/wp-content/uploads/2019/12/kidney.jpg
# To: /images/2019/12/kidney.jpg
```

Or keep them as external references - they work fine!

### Step 8.5: Add Caption Styling CSS (Recommended)

Your WordPress caption shortcodes have been converted to `<figure>` tags with alignment classes (`aligncenter`, `alignleft`, `alignright`). Add CSS to style them properly.

**Download `wordpress-caption-styles.css` from Claude**, then add to your theme:

**Option 1: Global styles file**
```bash
# Create/edit base styles
vim src/assets/styles/base.css

# Paste the CSS from wordpress-caption-styles.css
```

**Option 2: Blog post component**
Find your blog post layout component (likely `src/layouts/BlogPost.astro` or similar) and add a `<style>` section with the caption CSS.

**What this CSS does:**
- Centers `.aligncenter` images
- Floats `.alignleft` images left with text wrap
- Floats `.alignright` images right with text wrap
- Makes everything responsive on mobile
- Styles captions consistently

### Step 9: Customize AstroWind (Optional)

**Site config** - `src/config.yaml`:
```yaml
site:
  name: 'Mike Roberto'
  title: 'Mike Roberto - PricePlow & Personal Blog'
  description: 'Supplements, beverages, entrepreneurship, and more'
  
blog:
  postsPerPage: 10
```

**Colors** - Look for CSS variables in:
- `src/assets/styles/tailwind.css`
- AstroWind uses Tailwind, so customize via `tailwind.config.js`

### Step 10: Commit and Push

```bash
cd ~/perl/astro/mikeroberto-astro

git add .
git status  # Review what's being committed

git commit -m "WordPress to AstroWind migration complete

- Converted 61 blog posts with 290 archived comments
- Preserved WordPress /YYYY/slug URL structure via filenames
- Migrated categories, tags, and metadata
- Created 109 Cloudflare redirects from WordPress Redirection plugin
- New posts can use clean /slug URLs without year prefix"

# Push to GitHub
git push origin main --force  # --force because we replaced everything
```

### Step 11: Deploy to Cloudflare Pages

**In Cloudflare Dashboard:**
1. Go to Workers & Pages
2. Create application → Connect to Git
3. Select `clutchwave/mikeroberto-blog`
4. Configure:
   - Framework preset: **Astro**
   - Build command: `npm run build`
   - Build output: `dist`
   - Node version: `22`
5. Deploy!

The `_redirects` file will automatically work.

## Troubleshooting

**Problem: Build fails with schema error**
```
Error: Invalid frontmatter in src/data/post/some-post.md
```
**Fix:** Check that post's frontmatter matches AstroWind schema. Common issues:
- Empty strings should be removed or have values
- Date must be in `YYYY-MM-DD` format
- Category must be a single string, not array

**Problem: Posts not showing up**
**Fix:** Check AstroWind uses `src/data/post/` not `src/content/blog/`

**Problem: URLs are wrong**
**Fix:** Check directory structure matches expected format:
- Old posts: `src/data/post/2019/high-protein-kidney.md` → `/2019/high-protein-kidney`
- New posts: `src/data/post/my-article.md` → `/my-article`
Also verify `src/content/config.ts` uses `**/*.md` pattern (not `*.md`).

**Problem: Images broken**
**Fix:** External WordPress URLs should still work. If not, check the original URL is still live.

## What Got Migrated

✅ **Successfully Migrated:**
- 61 published WordPress posts
- WordPress /YYYY/slug URLs preserved exactly as-is
- 290 comments (archived as static HTML)
- 17 categories (first category per post)
- 129 tags
- All metadata (titles, dates, excerpts)
- 109 WordPress Redirection plugin redirects
- Full flexibility for future posts (with or without year prefix)

⚠️ **May Need Manual Attention:**
- Images still point to WordPress URLs (work fine, but could migrate)
- Multiple categories per post → AstroWind uses single category
- Custom WordPress shortcodes (if any remain)

## Custom Fields Added

Your posts have these extra fields for reference:
- `wpSlug` - Original WordPress slug
- `wpYear` - Original post year
- `comments_count` - Number of archived comments

These aren't used by AstroWind but help you track the migration.

## Next Steps

1. **Test thoroughly** - Click through your site, test redirects
2. **Customize design** - Update colors, fonts, layout as desired
3. **Add new content** - Create posts directly in `src/data/post/`
4. **Set up analytics** - Cloudflare Web Analytics is free
5. **Custom domain** - Point DNS to Cloudflare Pages

## Getting Help

If something goes wrong:
1. Check `migration-report.json` for the full inventory
2. Compare a converted post to an AstroWind example post
3. Test the build locally before pushing
4. Ask me in Claude! Reference this file and the specific issue

---

**Migration completed by:** Claude (Sonnet 4.5)
**Date:** December 2025
**Source:** WordPress XML export
**Destination:** AstroWind (Astro 5)
