# GitHub Actions Build Guide

This project is configured to automatically build executables for macOS, Windows, and Linux using GitHub Actions.

## Initial Setup

### 1. Create a GitHub Repository

If you haven't already:

```bash
cd "/Users/nathan/Documents/ModScan Tool"
git init
git add .
git commit -m "Initial commit"
```

Then create a new repository on GitHub and push:

```bash
git remote add origin https://github.com/YOUR_USERNAME/modscan-tool.git
git branch -M main
git push -u origin main
```

### 2. Add Your Icon (Optional)

Place your `icon.png` file in the project root before committing:

```bash
# After you have your icon.png file
git add icon.png
git commit -m "Add application icon"
git push
```

## How Builds Work

### Automatic Builds

Builds trigger automatically on:
- **Every push** to `main` or `master` branch
- **Every pull request**
- **Manual trigger** (see below)
- **Release creation** (see below)

### Where to Find Your Builds

1. Go to your GitHub repository
2. Click the **"Actions"** tab
3. Click on the latest workflow run
4. Scroll down to **"Artifacts"** section
5. Download:
   - `ModScan-Tool-macOS` (contains .app and .dmg)
   - `ModScan-Tool-Windows` (contains .exe)
   - `ModScan-Tool-Linux` (contains .tar.gz)

## Manual Build Trigger

You can manually trigger a build anytime:

1. Go to **Actions** tab
2. Click **"Build ModScan Tool"** workflow
3. Click **"Run workflow"** button
4. Select branch and click **"Run workflow"**

## Creating a Release

To create an official release with downloads:

```bash
# Tag your current commit
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

Then on GitHub:
1. Go to **Releases** → **"Draft a new release"**
2. Select your tag (v1.0.0)
3. Write release notes
4. Click **"Publish release"**

The executables will be **automatically attached** to the release!

## Build Times

Approximate build times:
- macOS: 8-12 minutes
- Windows: 6-10 minutes
- Linux: 5-8 minutes

**Total**: ~15-20 minutes for all platforms (they run in parallel)

## Troubleshooting

### Build fails with "No module named X"

Add the missing module to `requirements.txt`:
```bash
echo "module_name" >> requirements.txt
git add requirements.txt
git commit -m "Add missing dependency"
git push
```

### Icon not appearing

Make sure:
- `icon.png` is in the project root
- It's committed to git: `git add icon.png`
- It's 512x512 or larger

### Builds work but app won't run

**macOS**:
```bash
xattr -cr "/path/to/ModScan Tool.app"
```

**Windows**: Right-click → Properties → Unblock

**Linux**:
```bash
chmod +x modscan-tool
```

## Free Tier Limits

GitHub Actions is free for public repositories with:
- 2,000 minutes/month for private repos
- Unlimited minutes for public repos

Each full build uses ~30 minutes total (10 min × 3 platforms in parallel).

## Viewing Build Logs

If a build fails:
1. Click on the failed workflow run
2. Click on the failing job (e.g., "Build on ubuntu-latest")
3. Expand the failing step to see error details

## Files Generated

After a successful build:

```
dist/
├── ModScan-Tool-macOS.dmg          # macOS installer
├── ModScan Tool.app/                # macOS application
├── ModScan-Tool-Windows.exe         # Windows executable
└── ModScan-Tool-Linux.tar.gz        # Linux package
```

## Next Steps

1. ✅ Push your code to GitHub
2. ✅ Add icon.png if you have one
3. ✅ Wait for builds to complete (~15-20 min)
4. ✅ Download artifacts from Actions tab
5. ✅ Test on each platform
6. ✅ Create a release when ready!

Enjoy your cross-platform builds! 🚀
