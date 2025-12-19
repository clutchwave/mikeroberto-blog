# URL Strategy for Mike Roberto Blog

## The Approach

**WordPress URLs are preserved exactly as they were.** No redirects needed.

## How It Works

AstroWind generates URLs from the **file path** (not just filename):

```
File Path                                 →  URL
src/data/post/2019/high-protein-kidney.md →  /2019/high-protein-kidney
src/data/post/2024/blood-work.md          →  /2024/blood-work
src/data/post/my-new-post.md              →  /my-new-post
```

**Key insight:** The directory structure creates the URL structure!

## Migration Strategy

**Old WordPress posts (61 posts):**
- Organized in year subdirectories: `src/data/post/YYYY/slug.md`
- URL matches WordPress exactly: `/YYYY/slug`
- Example: `src/data/post/2019/high-protein-kidney.md` → `/2019/high-protein-kidney`
- ✅ All existing links work perfectly
- ✅ SEO preserved
- ✅ No redirects needed

**New posts you write:**
- You choose where to put them
- Want clean URL? → `src/data/post/article-name.md` → `/article-name`
- Want year? → `src/data/post/2025/article-name.md` → `/2025/article-name`
- Complete flexibility going forward

## What About Redirects?

The `_redirects` file only contains:
- Redirects from WordPress Redirection plugin (109 redirects)
- These are for old URLs you explicitly redirected in WordPress
- No automatic year-based redirects (not needed!)

## Examples

**Migrated post URLs (work as-is):**
- File: `src/data/post/2019/high-protein-kidney.md`
  URL: `https://www.mikeroberto.com/2019/high-protein-kidney` ✓
- File: `src/data/post/2024/blood-work-july-2024.md`
  URL: `https://www.mikeroberto.com/2024/blood-work-july-2024` ✓
- File: `src/data/post/2006/fellow-buckeyes-so-you-wanna-visit-austin.md`
  URL: `https://www.mikeroberto.com/2006/fellow-buckeyes-so-you-wanna-visit-austin` ✓

**New post you might write:**
- File: `src/data/post/2025/protein-trends.md` → URL: `/2025/protein-trends`
- File: `src/data/post/favorite-supplements.md` → URL: `/favorite-supplements`
- Your choice!

## Why This Works

1. **AstroWind uses file-path-based routing** (not frontmatter slugs)
2. **Directory structure = URL structure**
3. **Year directories create /YYYY/ in URLs**
4. **Old content maintains exact WordPress URLs**
5. **New content can be whatever you want**

## Checking Your URLs

After migration, test a few:
```bash
npm run dev

# Check directory structure
ls -l src/data/post/2019/

# Then visit:
http://localhost:4321/2019/high-protein-kidney
http://localhost:4321/2024/blood-work-july-2024
```

Should work perfectly! 🎯
