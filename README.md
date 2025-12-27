[memory_manager_v1.1.0_README.md](https://github.com/user-attachments/files/24351656/memory_manager_v1.1.0_README.md)
# Memory Manager 📸

**Automatically download and organize all your Snapchat memories from your data export.**

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey.svg)

<p align="center">
  <a href="https://buymeacoffee.com/ethanshoforost">
    <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="150">
  </a>
</p>

---

## ✨ Features

- 📥 **Automatic Downloads** - Downloads all photos and videos from your Snapchat export
- 🎨 **Overlay Merging** - Automatically merges Snapchat overlays with your memories
- 📅 **Correct Dates** - Files are named by actual date taken (converted to your timezone)
- 🔖 **Automatic Metadata** - Photos and videos have correct dates in their metadata! *(NEW in v1.1.0)*
- ⏸️ **Pause & Resume** - Pause and resume downloads anytime
- 🔄 **Retry Failed** - Automatically retry failed downloads
- 📊 **Progress Tracking** - Real-time progress with success/fail counts
- 💻 **Cross-Platform** - Works on Windows and Mac

---

## 📥 Download & Python Requirements

### ⚠️ **Python 3.11.9 Required for Auto-Install**

Memory Manager works best with **Python 3.11.9** - libraries install automatically.

**Download Python 3.11.9:**
- 🪟 **Windows:** [python-3.11.9-amd64.exe](https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe)
- 🍎 **Mac:** [python-3.11.9-macos11.pkg](https://www.python.org/ftp/python/3.11.9/python-3.11.9-macos11.pkg)

**⚠️ During Installation: CHECK "Add Python to PATH"!**

---

### Download Memory Manager

**Windows:** [`Memory_Manager.pyw`](windows/Memory_Manager.pyw)  
**Mac:** [`Memory_Manager_Mac.zip`](mac/Memory_Manager_Mac.zip)

**Latest Release:** [v1.1.0](https://github.com/EthanShoforost/Memory-Manager/releases/latest) - Now with automatic metadata fixing!

---

## 📚 Installation & Usage

**Complete installation guides available:**

- 📘 [**Windows Guide**](../../raw/main/docs/Memory_Manager_Windows_Guide.docx) ⬇️ Download
- 📗 [**Mac Guide**](../../raw/main/docs/Memory_Manager_Mac_Guide.docx) ⬇️ Download

### Quick Start

#### Windows:
1. **Install Python 3.11.9** (link above) - **CHECK "Add Python to PATH"**
2. Download `Memory_Manager.pyw`
3. Double-click to run
4. Click "Yes" when asked to install libraries
5. Wait 1-2 minutes
6. Done! ✨

#### Mac:
1. **Install Python 3.11.9** (link above)
2. Download and extract `Memory_Manager_Mac.zip`
3. Run "1 - Run Setup (First Time Only)"
4. Run "2 - Open Memory Manager"
5. Done! ✨

**Having Python 3.12+?** See troubleshooting section below.

---

## 🎯 How to Use

### Step 1: Get Your Snapchat Data
1. Go to [Snapchat Account Settings](https://accounts.snapchat.com/accounts/downloadmydata)
2. Request your data export
3. Wait for email (can take 24 hours)
4. Download and extract the ZIP file

### Step 2: Run Memory Manager
1. Open Memory Manager
2. Select your Snapchat HTML file (`memories_history.html`)
3. Choose where to save your memories
4. Click "Start Download"
5. Wait for downloads to complete ✨

**Your memories are now organized by date with correct metadata!**

---

## 🆕 What's New in v1.1.0

### Automatic Metadata Fixing!

Your downloaded photos and videos now have the **correct dates in their metadata**:

- ✅ **Photos** - EXIF data written automatically (`DateTimeOriginal`, etc.)
- ✅ **Videos** - File timestamps updated to match actual date
- ✅ **Photo libraries** - Memories appear in correct chronological order
- ✅ **Zero extra steps** - Happens automatically during download

**Upgrading from v1.0.x?** Your old files don't have metadata. Either:
- Re-download with v1.1.0 (metadata added automatically)
- Use the [Snapchat Metadata Fixer](https://github.com/ethanshoforost/snapchat-metadata-fixer) to fix existing files

---

## 🐛 Troubleshooting

### I Have Python 3.12, 3.13, or 3.14

**Auto-install won't work with Python 3.12+.** You have two options:

#### Option A: Install Python 3.11.9 (Recommended)

1. **Uninstall your current Python:**
   - Windows: Settings → Apps → Search "Python" → Uninstall
   - Mac: Delete `/Applications/Python 3.xx`

2. **Install Python 3.11.9** (links at top of page)

3. **Run Memory Manager** - auto-install will work!

#### Option B: Manually Install Libraries (Keep Python 3.12+)

**Windows:**
1. Open **Command Prompt**
2. Copy and paste this command:
   ```
   python -m pip install requests beautifulsoup4 Pillow opencv-python numpy piexif
   ```
3. Press Enter and wait for installation to complete
4. Run Memory Manager

**Mac:**
1. Open **Terminal**
2. Copy and paste this command:
   ```
   pip3 install requests beautifulsoup4 Pillow opencv-python numpy piexif
   ```
3. Press Enter and wait for installation to complete
4. Run Memory Manager

**If you get errors:** Python 3.14+ may not be supported yet. Use Python 3.11.9 instead.

---

### Other Common Issues

**"Python not found" or "python is not recognized"**
- You didn't check "Add Python to PATH" during installation
- Solution: Reinstall Python 3.11.9 and **check the PATH box**

**"Permission denied" or "Access denied"**
- Windows: Run Command Prompt as Administrator
- Mac: Try `sudo pip3 install ...` (will ask for password)

**Mac Security Warnings**
- See the complete [Mac Installation Guide](../../raw/main/docs/Memory_Manager_Mac_Guide.docx)

**Libraries install but program won't open**
- Make sure you're using Python 3.11.9, not 3.12+
- Try uninstalling and reinstalling Python

---

### Need More Help?

Check the complete installation guides:
- 📘 [Windows Guide](../../raw/main/docs/Memory_Manager_Windows_Guide.docx)
- 📗 [Mac Guide](../../raw/main/docs/Memory_Manager_Mac_Guide.docx)

---

## 🔗 Related Tools

**NEW:** [**Snapchat Metadata Fixer**](https://github.com/ethanshoforost/snapchat-metadata-fixer) - Standalone tool to fix metadata on existing files
- Fix files downloaded with Memory Manager v1.0.x
- Full video metadata support with FFmpeg
- Batch process entire folders

---

## ⚖️ Legal

This software is provided under the MIT License. By using this software, you agree to the terms of the [LICENSE](LICENSE) and acknowledge that the creator is not liable for any damages or issues that may arise from its use.

**Key Points:**
- Software is provided "AS IS" without warranty of any kind
- Use at your own risk
- Creator is not liable for any damages or data loss
- You are responsible for complying with Snapchat's Terms of Service

---

## ⚠️ Disclaimer

This tool is **not affiliated with, endorsed by, or connected to Snapchat Inc.**

Use at your own risk. Make sure you comply with Snapchat's Terms of Service when requesting and using your data export.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Ethan Shoforost

---

## ☕ Support

If Memory Manager helped you preserve your memories, consider supporting development!

<a href="https://buymeacoffee.com/ethanshoforost">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="150">
</a>

Your support helps maintain and improve this project! 🙏

---

## 📧 Contact

Created by **Ethan Shoforost**

- GitHub: [@ethanshoforost](https://github.com/ethanshoforost)  
- Support: [Buy Me a Coffee](https://buymeacoffee.com/ethanshoforost)

---

<p align="center">
  <strong>Happy Memory Preserving! 📸✨</strong>
</p>
