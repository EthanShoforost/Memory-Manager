# Memory Manager 📸

Download and organize all your Snapchat memories automatically!

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-blue)](https://github.com/ethanshoforost/memory-manager)

<p align="center">
  <a href="https://buymeacoffee.com/ethanshoforost">
    <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="150">
  </a>
</p>

---

## 🎯 What is Memory Manager?

Memory Manager is a desktop application that helps you download and organize **all** your Snapchat memories from your data export. Instead of manually downloading hundreds or thousands of photos and videos one by one, this tool automates the entire process.

### ✨ Key Features

- ⚡ **Automated Downloads** - Download all memories with one click
- 📅 **Smart Organization** - Files automatically named by date and time
- 🎨 **Overlay Merging** - Text, stickers, and filters merged with your media
- ⏸️ **Pause & Resume** - Full control over the download process
- 🔄 **Retry Failed Downloads** - Automatically retry any failed downloads
- 🔒 **100% Private** - All processing happens on your computer
- 💻 **Cross-Platform** - Works on Windows and macOS

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
3. Run "1 - Run Setup (First Time Only)"
4. Run "2 - Memory Manager"

**Note for Mac users:** The first time you open the files, you'll need to bypass Mac's security warnings. See the [Mac Guide](docs/Memory_Manager_Mac_Guide.docx) for detailed instructions.

---

## 🔐 Privacy & Security

Your privacy is the top priority:

- ✅ **Everything Stays Local** - Runs entirely on your computer
- ✅ **No Data Collection** - No analytics, tracking, or data harvesting
- ✅ **Direct Downloads** - Connects directly to Snapchat's servers
- ✅ **No Account Required** - Just your data export file
- ✅ **Open Source** - Review the code yourself

---

## 🚀 How It Works

1. **Get Your Data** - Request your memories from Snapchat (Settings → My Data)
2. **Extract** - Unzip the download and find the "mydata" folder
3. **Select** - Open Memory Manager and select your "mydata" folder
4. **Download** - Click "Start Download" and let it run
5. **Enjoy** - All your memories organized in one folder!

### File Naming

Files are automatically named using the format: `YYYY-MM-DD_HH-MM-SS.extension`

Examples:
- `2024-03-15_14-30-45.jpg` = March 15, 2024 at 2:30:45 PM
- `2023-12-25_09-15-00.mp4` = December 25, 2023 at 9:15:00 AM

---

## ⚙️ Technical Details

### Built With
- Python 3.10+
- Tkinter (GUI)
- Requests (HTTP)
- BeautifulSoup4 (HTML parsing)
- Pillow & OpenCV (Image processing)
- NumPy (Array operations)

### System Requirements

**Windows:**
- Windows 10 or newer
- Python 3.10 or newer
- 100MB+ free disk space (plus space for your memories)

**macOS:**
- macOS 10.13 or newer
- Python 3.10 or newer
- 100MB+ free disk space (plus space for your memories)

---

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest new features
- Submit pull requests
- Improve documentation

---

## ⚠️ Disclaimer

This tool is **not affiliated with, endorsed by, or connected to Snapchat Inc.**

Use at your own risk. The creator is not responsible for any issues that may arise from using this software. Make sure you comply with Snapchat's Terms of Service when requesting and using your data export.

---

## ⚖️ Legal

This software is provided under the MIT License. By using this software, you agree to the terms of the [LICENSE](LICENSE) and acknowledge that the creator is not liable for any damages or issues that may arise from its use.

**Key Points:**
- Software is provided "AS IS" without warranty of any kind
- Use at your own risk
- Creator is not liable for any damages or data loss
- You are responsible for complying with Snapchat's Terms of Service

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Ethan Shoforost

---

## ☕ Support

If Memory Manager helped you preserve your memories, consider buying me a coffee!

<a href="https://buymeacoffee.com/ethanshoforost">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="150">
</a>

Your support helps maintain and improve this project! 🙏

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
   python -m pip install requests beautifulsoup4 Pillow opencv-python numpy
   ```
3. Press Enter and wait for installation to complete
4. Run Memory Manager

**Mac:**
1. Open **Terminal**
2. Copy and paste this command:
   ```
   pip3 install requests beautifulsoup4 Pillow opencv-python numpy
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

## 📧 Contact

Created by **Ethan Shoforost**

- GitHub: [@ethanshoforost](https://github.com/ethanshoforost)
- Support: [Buy Me a Coffee](https://buymeacoffee.com/ethanshoforost)

---

<p align="center">
  <strong>Happy Memory Organizing! 📸✨</strong>
</p>
