#!/bin/bash
# WordPress to AstroWind Migration - Step by Step
# Run this from your mikeroberto-astro directory

set -e  # Exit on error

echo "========================================="
echo "WordPress to AstroWind Migration Script"
echo "========================================="
echo ""

# Check we're in the right directory
if [ ! -f "astro.config.mjs" ] && [ ! -f "astro.config.ts" ]; then
    echo "ERROR: Not in AstroWind directory (no astro.config found)"
    echo "Please cd to ~/perl/astro/mikeroberto-astro first"
    exit 1
fi

# Create migration-tools directory
echo "Step 1: Setting up migration tools..."
mkdir -p migration-tools
cd migration-tools

# Check for required files
if [ ! -f "../convert-wordpress-astrowind.py" ]; then
    echo "ERROR: convert-wordpress-astrowind.py not found"
    echo "Please copy it to the mikeroberto-astro directory"
    exit 1
fi

if [ ! -f "../convert-redirects-astrowind.py" ]; then
    echo "ERROR: convert-redirects-astrowind.py not found"
    echo "Please copy it to the mikeroberto-astro directory"
    exit 1
fi

# Copy scripts
cp ../convert-wordpress-astrowind.py .
cp ../convert-redirects-astrowind.py .
chmod +x *.py

echo "✓ Migration tools ready"
echo ""

# Step 2: Copy WordPress data
echo "Step 2: Copy WordPress export files..."
echo "Please copy these files into migration-tools/:"
echo "  1. mikeroberto-wordpress-export-EVERYTHING-for-comments-2025-12-18.xml"
echo "  2. redirection-www-mikeroberto-com-december-17-2025.json"
echo ""
echo "From your backup directory, run:"
echo "  cp ~/perl/astro/mikeroberto-astro-backup/migration-tools/*.xml ~/perl/astro/mikeroberto-astro/migration-tools/"
echo "  cp ~/perl/astro/mikeroberto-astro-backup/migration-tools/*.json ~/perl/astro/mikeroberto-astro/migration-tools/"
echo ""
read -p "Press Enter when files are copied..."

# Verify files exist
if [ ! -f "mikeroberto-wordpress-export-EVERYTHING-for-comments-2025-12-18.xml" ]; then
    echo "ERROR: WordPress XML export not found"
    exit 1
fi

if [ ! -f "redirection-www-mikeroberto-com-december-17-2025.json" ]; then
    echo "ERROR: Redirects JSON not found"
    exit 1
fi

echo "✓ WordPress data files ready"
echo ""

# Step 3: Convert blog posts
echo "Step 3: Converting WordPress posts to AstroWind format..."
python3 ./convert-wordpress-astrowind.py \
    mikeroberto-wordpress-export-EVERYTHING-for-comments-2025-12-18.xml \
    --output-dir ../src/data/post \
    --report migration-report.json

echo ""
echo "✓ Blog posts converted (organized by year in subdirectories)"
echo ""

# Step 3.5: Update content config
echo "Step 3.5: IMPORTANT - Update content config for subdirectories..."
echo "You need to edit src/content/config.ts and change:"
echo "  FROM: pattern: ['*.md', '*.mdx']"
echo "  TO:   pattern: ['**/*.md', '**/*.mdx']"
echo ""
echo "This makes AstroWind look in year subdirectories (2019/, 2024/, etc.)"
echo ""
read -p "Press Enter after updating src/content/config.ts..."

# Step 4: Generate redirects
echo "Step 4: Generating Cloudflare redirects..."
python3 ./convert-redirects-astrowind.py \
    redirection-www-mikeroberto-com-december-17-2025.json \
    --output ../public/_redirects \
    --migration-report migration-report.json

echo ""
echo "✓ Redirects generated"
echo ""

# Step 5: Verify
echo "Step 5: Verification..."
POST_COUNT=$(ls -1 ../src/data/post/*.md 2>/dev/null | wc -l)
echo "  Posts created: $POST_COUNT"

if [ -f "../public/_redirects" ]; then
    REDIRECT_COUNT=$(grep -c "^/" ../public/_redirects || true)
    echo "  Redirects created: $REDIRECT_COUNT"
fi

echo ""
echo "========================================="
echo "Migration Complete! 🎉"
echo "========================================="
echo ""
echo "WordPress URLs preserved:"
echo "  - Old posts use /YYYY/slug format (via filenames: YYYY-slug.md)"
echo "  - New posts can use clean /slug format (no year needed)"
echo ""
echo "Next steps:"
echo "  1. Review posts: ls -la ../src/data/post/"
echo "  2. Test build: cd .. && npm run dev"
echo "  3. Check a WordPress URL: http://localhost:4321/2019/high-protein-kidney"
echo "  4. Check migration report: cat migration-tools/migration-report.json"
echo "  5. Verify redirects: cat public/_redirects | head -20"
echo ""
echo "When ready to deploy:"
echo "  git add ."
echo "  git commit -m 'WordPress to AstroWind migration complete'"
echo "  git push"
