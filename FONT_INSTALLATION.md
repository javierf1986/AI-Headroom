# Perfect DOS VGA 437 Font Installation

## Option 1: Local System Font Installation (Best Quality)

### Step 1: Download the font
Visit one of these sources:
- **FontSquirrel**: https://www.fontspace.com/download/family/perfect-dos-vga-437
- **GitHub**: https://github.com/spacemodule/perfect-dos-vga-437/releases

Download the TrueType font file (`.ttf`)

### Step 2: Install to Windows Fonts folder
1. Extract the downloaded file (if zipped)
2. Right-click the `.ttf` file → **Install for all users** (or Install)
   - OR: Drag the `.ttf` file to `C:\Windows\Fonts` folder
3. Wait for installation to complete

### Step 3: Verify installation
- Open Control Panel → Fonts
- Search for "Perfect DOS VGA 437"
- You should see it listed

### Step 4: Clear browser cache and refresh
- In your browser: **Ctrl + Shift + Delete** (Open DevTools Cache)
- Or Hard Refresh: **Ctrl + Shift + R**
- Visit http://localhost:5177 and verify the font is applied

## Option 2: Web Font (Automatic Fallback)
The CSS has been updated with @font-face declarations that serve the font from a web CDN. If the system font isn't found, the web version will automatically load.

**No additional action needed** - the web font will work immediately without installation.

### Which will users see?
1. **If system font installed**: Perfect DOS VGA 437 (local) - Fastest & best quality
2. **If not installed**: Perfect DOS VGA 437 (web font) - Still authentic, slight network delay
3. **If both fail**: IBM Plex Mono (fallback) - Excellent retro alternative

---

Once installed, hard refresh the browser to see the change take effect!
