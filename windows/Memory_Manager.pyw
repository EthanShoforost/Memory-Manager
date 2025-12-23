#!/usr/bin/env python3
"""
Memory Manager - Snapchat Memories Downloader
Created by: Ethan Shoforost
Version: 1.0.0
GitHub: https://github.com/ethanshoforost/memory-manager
Support: https://buymeacoffee.com/ethanshoforost

A desktop application that helps you download and organize all your 
Snapchat memories from your data export.

Copyright (c) 2025 Ethan Shoforost
Licensed under the MIT License - see LICENSE file for details

DISCLAIMER:
This tool is not affiliated with, endorsed by, or connected to Snapchat Inc.
Use at your own risk. The creator is not responsible for any issues that may
arise from using this software. Make sure you comply with Snapchat's Terms
of Service when requesting and using your data export.
"""

import sys
import subprocess
import os

# Silent package check
def install_package(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

required_packages = {'requests': 'requests', 'beautifulsoup4': 'bs4', 'Pillow': 'PIL', 'opencv-python': 'cv2', 'numpy': 'numpy'}
missing_packages = []
for p, i in required_packages.items():
    try:
        __import__(i)
    except ImportError:
        missing_packages.append(p)

if missing_packages:
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    if messagebox.askyesno("Install Libraries", f"Missing: {', '.join(missing_packages)}\n\nInstall now?"):
        for pkg in missing_packages:
            install_package(pkg)
        messagebox.showinfo("Success", "Libraries installed! Restarting...")
        root.destroy()
        os.execl(sys.executable, sys.executable, *sys.argv)
    else:
        root.destroy()
        sys.exit()

import requests, zipfile, io, shutil, threading
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import cv2, numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import time

def merge_overlay_with_video(video_path, overlay_path, output_path):
    try:
        cap = cv2.VideoCapture(video_path)
        fps, w, h = int(cap.get(cv2.CAP_PROP_FPS)), int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        overlay = cv2.imread(overlay_path, cv2.IMREAD_UNCHANGED)
        if overlay is None: return False
        if overlay.shape[1] != w or overlay.shape[0] != h: overlay = cv2.resize(overlay, (w, h))
        has_alpha = overlay.shape[2] == 4 if len(overlay.shape) == 3 else False
        overlay_bgr = overlay[:,:,:3] if has_alpha else overlay
        overlay_alpha = overlay[:,:,3:]/255.0 if has_alpha else np.ones((h,w,1))
        out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
        if not out.isOpened(): cap.release(); return False
        while True:
            ret, frame = cap.read()
            if not ret: break
            if has_alpha: frame = (frame.astype(float)*(1-overlay_alpha) + overlay_bgr*overlay_alpha).astype(np.uint8)
            out.write(frame)
        cap.release(); out.release()
        return True
    except: return False

def merge_overlay_with_image(image_path, overlay_path, output_path):
    try:
        base, overlay = Image.open(image_path), Image.open(overlay_path)
        if overlay.size != base.size: overlay = overlay.resize(base.size, Image.LANCZOS)
        if base.mode != 'RGBA': base = base.convert('RGBA')
        if overlay.mode != 'RGBA': overlay = overlay.convert('RGBA')
        combined = Image.alpha_composite(base, overlay)
        if output_path.lower().endswith('.png'): combined.save(output_path, 'PNG')
        else: combined.convert('RGB').save(output_path, 'JPEG', quality=95)
        return True
    except: return False

def convert_utc_to_local(date_string):
    """Convert UTC timestamp from Snapchat to local timezone"""
    try:
        # Remove ' UTC' suffix if present
        date_string = date_string.replace(' UTC', '').strip()
        
        # Parse the UTC datetime
        utc_dt = datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
        
        # Convert UTC to timestamp (treating it as UTC, not local)
        # Use calendar.timegm instead of time.mktime to treat input as UTC
        import calendar
        utc_timestamp = calendar.timegm(utc_dt.timetuple())
        
        # Convert timestamp to local time
        local_dt = datetime.fromtimestamp(utc_timestamp)
        
        # Format as YYYY-MM-DD_HH-MM-SS
        return local_dt.strftime('%Y-%m-%d_%H-%M-%S')
    except:
        # If conversion fails, fall back to original method
        return date_string.replace(' UTC', '').replace(' ', '_').replace(':', '-')


class SnapDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Memory Manager")
        self.root.geometry("1000x800")
        self.root.minsize(900, 750)
        
        # Colors
        self.yellow = "#FFD700"
        self.orange = "#FF6B35"
        self.white = "#FFFFFF"
        self.green = "#06D6A0"
        self.blue = "#3B82F6"
        self.dark = "#2D3748"
        self.light = "#718096"
        
        # State
        self.html_file = None
        self.output_dir = None
        self.is_downloading = False
        self.paused = False
        self.memories = []
        self.failed_memories = []
        self.stats = {'processed': 0, 'failed': 0}
        
        # Show welcome dialog
        self.show_welcome_dialog()
        
        # Create UI
        self.create_ui()
    
    def show_welcome_dialog(self):
        """Welcome dialog with instructions."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Welcome")
        dialog.geometry("650x700")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (325)
        y = (dialog.winfo_screenheight() // 2) - (350)
        dialog.geometry(f"650x700+{x}+{y}")
        
        # Header
        header = tk.Frame(dialog, bg=self.orange, height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="👋 Welcome!", font=("Segoe UI", 24, "bold"), bg=self.orange, fg="white").pack(expand=True)
        
        # Content
        content = tk.Frame(dialog, bg="white")
        content.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        tk.Label(content, text="Before You Start", font=("Segoe UI", 16, "bold"), bg="white", fg=self.dark).pack(anchor='w', pady=(0, 15))
        
        instructions = [
            ("1️⃣", "Move Content Out of 'My Eyes Only'", "Go to Snap > My Eyes Only\nMove ALL memories to regular Memories\n(My Eyes Only content won't be in export)"),
            ("2️⃣", "Request Your Data from Snap", "Open Snap > Settings > My Data\nClick 'Submit Request'\nWait 24-48 hours for email"),
            ("3️⃣", "Download Your Data Package", "Check your email from Snap\nDownload the data package\nExtract the ZIP file"),
            ("⚠️", "Important: Download Immediately!", "URLs expire in 24-72 hours\nRun this app RIGHT AFTER downloading")
        ]
        
        for emoji, title, desc in instructions:
            frame = tk.Frame(content, bg="#F7FAFC")
            frame.pack(fill=tk.X, pady=(0, 12))
            
            inner = tk.Frame(frame, bg="#F7FAFC")
            inner.pack(padx=15, pady=12)
            
            header_row = tk.Frame(inner, bg="#F7FAFC")
            header_row.pack(anchor='w', fill=tk.X)
            
            tk.Label(header_row, text=emoji, font=("Segoe UI", 18), bg="#F7FAFC").pack(side=tk.LEFT, padx=(0, 8))
            tk.Label(header_row, text=title, font=("Segoe UI", 10, "bold"), bg="#F7FAFC", fg=self.dark).pack(side=tk.LEFT)
            tk.Label(inner, text=desc, font=("Segoe UI", 9), bg="#F7FAFC", fg=self.light, justify=tk.LEFT, anchor='w').pack(anchor='w', padx=(30, 0), pady=(4, 0))
        
        # Requirements
        req_box = tk.Frame(content, bg="#FFF5F5", highlightbackground="#FC8181", highlightthickness=2)
        req_box.pack(fill=tk.X, pady=(10, 0))
        req_inner = tk.Frame(req_box, bg="#FFF5F5")
        req_inner.pack(padx=15, pady=12)
        tk.Label(req_inner, text="📋 System Requirements", font=("Segoe UI", 10, "bold"), bg="#FFF5F5", fg="#C53030").pack(anchor='w', pady=(0, 5))
        tk.Label(req_inner, text="Python libraries will auto-install if missing:\nrequests, beautifulsoup4, Pillow, opencv-python, numpy", font=("Segoe UI", 8), bg="#FFF5F5", fg="#742A2A", justify=tk.LEFT, anchor='w').pack(anchor='w')
        
        # Button
        tk.Button(content, text="✓  I Understand, Let's Begin!", font=("Segoe UI", 13, "bold"), bg=self.green, fg="white", relief=tk.FLAT, padx=40, pady=15, cursor="hand2", command=dialog.destroy).pack(pady=(20, 0))
    
    def create_ui(self):
        """Create main UI - completely redesigned."""
        # Main container - yellow background
        main = tk.Frame(self.root, bg=self.yellow)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Content container - white
        content = tk.Frame(main, bg=self.white)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = tk.Frame(content, bg=self.orange, height=90)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        header_inner = tk.Frame(header, bg=self.orange)
        header_inner.pack(expand=True)
        
        # Custom ghost icon (embedded as base64)
        try:
            from PIL import Image, ImageTk
            import base64
            import io
            
            # Ghost icon data
            ghost_data = (
                "iVBORw0KGgoAAAANSUhEUgAABAAAAAQACAYAAAB/HSuDAAEAAElEQVR4nOz9eZwdZZn//7/vqlNV53S6"
                "OwlJ2ImyryK7IIooOCwzIqOg6Kgoio6DO36GD+M4joMzjj8XZkYHF/Q7LnxEUVHcEB0QQUVDCEE2UdYk"
                "BLKS9HLOqfX+/XFSxelOZ+mk+9Tp7tczj3p0ejt19zlVdeq67vu+bgkAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADA2EzZ"
                "DQAAANsWhqEdz88HQcB7PAAAAAAAAAAAMw29AwAATLIwDG0QBCbvxW/vnQ/D0Bpj5Pu+kaRGo2Eladmy"
                "ZWo0GqrX62o2m3rqqae0atUq1et1eZ6n4eHhEfsYHh5Ws9mUJFWrVe2zzz4jvl+r1WSMUX9/v+bOnatZ"
                "s2aN+P6sWbNUrVbV29urarWqnp4eua6rarVq2v+GRqNha7XaZvcPo/8OAADQfXiTBgBgJ0RRZLcn6B0Y"
                "GLBZlmlwcFDr1q3TypUrdf/99yuOY91///1as2aNli9frtWrV0uSNmzYoCzLZG1r5L/runIcR1mWKU1T"
                "GTNyl/nP5VzX3ezzKIq22kZjTLFJ0pw5c7RgwQLNnj1baZrqxS9+sXp7e3XEEUfogAMO0F577aXdd9/d"
                "jOd5AAAA5eGNGgCAHTA64M17xjds2GBXrVqlBx54QAMDA7r99tu1ceNGLV68WOvXr9fAwICstQqCQHEc"
                "q1KpKI7jIoA3xshaK8/zZIyR4zgyxqjRaBS9+M1mU1mWjWiP4ziqVCqSpDRNZa0dkSRI01SO48h1XWVZ"
                "ttnv+75ffN1aOyKhkLc3DMPiZ621cl1XCxYs0F577aWzzz5b++67r57//Ofruc99rvr7+7nHAACgy/Dm"
                "DADADlixYoVtNBp64IEHdNddd+nOO+/U8uXLtWLFCjUaDUVRJGutarWawjCUMaYI0JMkUaVSKXrkrbXq"
                "6elRvV6XJHmeVwTxeSDu+76kViCfpumYbQqCQJKKQH00z/MkSXEcb/a9PNFQqVRkjFEYhkXCwHEcOY6j"
                "NE3l+77q9bocxykex/O84m/KtyOOOEIHHXSQTjjhBB100EE6+uijNX/+fO47AAAoEW/EAAC0aTabVlIx"
                "9z2KIptlmR5++GH96le/0u9+9zstXrxYa9as0fDwsBqNhiRtNiR/vLY1pH9b3x/9+US1I/98W/vf0u87"
                "jiOplSR4znOeoxNOOEHPf/7z9Rd/8RfaddddNWfOnK3WDRirbgIAANgxvJkCAGakKIqspBHB5/DwsO3p"
                "6dG6dev0+OOPa+nSpbrlllu0dOlSLV++XIODgyOGwks7H/hv6XG6LQGws49prVWWZSNGGeyyyy466qij"
                "dPTRR+vcc8/Vfvvtp/7+fuUFE/Ogf+PGjTYIgiIpAwAAdgxvpACAGSnv2c+H2d9zzz269dZb9fOf/1xL"
                "ly7V8PDwiGH4vu8Xw+InKthuN50TAHk9grz+wJamMMybN09HHnmkTjnlFL3iFa/QPvvso912221EA6Io"
                "skmSqKenh3sYAADGiTdPAMCM9OSTT9rf/OY3+t73vqff/OY3WrFihTYtY6ckSUYUzTPGKI7jolBekiQT"
                "3p7pnACQpCzLVK1Wi/oCWZbJdd2iLkEYhkWiIE+2zJ07Vy9+8Yt16qmn6hWveIX23HNPzZo1i3sXAAB2"
                "EG+iAIBpr9Fo2I0bN2rRokW67rrrdMcdd+ixxx4b12NMRq9/u50NtCe6fRMV+Oe2ltDIvzd65YL2n+vp"
                "6dHcuXP1ghe8QC984Qv1N3/zN+rv71etVjPNZtNWq1WTr8QwoQ0HAGAa4U0SADBtrVq1yn7ve9/Tdddd"
                "p3vvvVcbNmxQmqbFEnzjQQJg52xvAmBL8pEZeQ0Bz/O0cOFCnXrqqTr55JP1V3/1V6rVasXrykgBAAA2"
                "x5sjAGBayHt/n3jiCfu///u/+vznP6+77rprRFDpOI6yLCv+Px4kAHbOziYAJMl13RHFBPPigtZaBUGg"
                "M844Q6997Wt19tlna9asWUWBxyiK7NZWGgAAYKbgzRAAMC184xvfsN/97nd1yy23qNlsKo7jEQF/bkfn"
                "uJMA2Dk7mwBofy09zyteX2OMsixTEASSpCiKNHv2bJ1yyin667/+a51zzjnq6elhBQEAAEQCAADQpQYG"
                "Bmx/f/9W36fuv/9+e/XVV+vaa6/Vhg0bFMfxZgH/tmxpnfuJNFaAO1nF9qaqiU5g5I/3nOc8RyeffLIu"
                "uOACvfCFL9T8+fOLJ5qaAQCAmYY3PQBA12sfwj08PGxvu+02feYzn9Gdd95ZLNc33sA/RwKgO0zGCIb8"
                "mKhWq4rjWHvssYde/epX661vfauOPPJII5EEAADMLLzhAQCmhCeffNLecMMN+sxnPqNHH320mAdurR1z"
                "qP/2IgHQHSZrBIAxRkEQFMsMStLcuXO1//776w1veIPe/va3q6enZ2Y/+QCAGYM3PABAV/v1r39tr732"
                "Wl133XUaGBgoir45jqMoimStle/7iqJohx6fBEB3mIwRAK7rynEcOY6jJEmUJImstapWq2o2m5Kk3Xbb"
                "Teecc47e97736fDDD5/ZLwIAAAAATKYwDG2z2RwR/a1du9ZeffXV9qijjrJBEFhJ1hgzrk3SmNt4H4et"
                "O7ctvb7b2kY/juM41nEc63mePfbYY+13vvMdOzg4OOJ4jKLI5sfqwMDA5FaDBABgEpHpBgB0jfvuu89+"
                "4xvf0De/+U2tXLlS0rMV38c7xH9LPcpmhve0TxeTsSqDMUae52m33XbTJZdcote//vVauHChyRMAksRy"
                "ggCAqYw3MQBAaaIostZa3Xnnnfqv//ov/fSnP9XQ0JB835e1thiy7fu+4jguu7noIpOVAHAcR0EQqNFo"
                "aP78+TrvvPP0nve8R8997nPl+77SNCUJAAAAAADjUa/X7Ze//GV72GGHFcP8Xde1rusWw7Il2SAIbBAE"
                "pQ85Z+uuTTs4BWBLm+u6VpKtVqvWcRxrjLG+71vXdW21WrWvf/3r7dKlSxn+DwAAAABb0z6Eenh42H7t"
                "a1+zCxcutNVqdUTQ1b6VHWCydfemCU4AjN7y/eT1ARzHsbVazb7mNa+xv/3tb237Mb2l/wMA0G0YwgYA"
                "mDRRFNksyxQEgYaGhvRf//Vf+u///m+tW7dOxphibn9e1b/dZAzxxvTRiePDtNWLMJuWE0ySRK7r6vjj"
                "j9dHP/pRvexlLyt+qF6v20qlwhQBAAAAADPX5z//ebv33nsXw/rzntW8p3907z8jANi2tWmSRwCMtRlj"
                "rOu61vM829vba3t7e+2pp55qf/nLX5KtAgAAADCz/fSnP7X77LNPEUDlc/3bt/Z5/2UHlWxTZxt9HHVi"
                "8zxvRF0ASdZxHOv7vn3pS19qFy9eTCIAAAAAwPTXPvf5T3/6k33JS15ifd+3vu+PmFPNxjYRm0pIALRv"
                "Y7XHcRz7vve9zy5fvtxKUqPRICEAAAAAYHoIw3BEMbT169fbD3zgA7avr68o7Od5XhEgjSegKzvAZOvu"
                "bfTxUvbmeV4xyiUIAvumN73Jbty40UpSs9kkEQAAAABgegjD0F511VXFcP+81z9fWm17lvETCYCObNOl"
                "xsLo46XszRhjgyCwtVqtOPbnzZtnr/3mtTaJE8vqAAAAAACmvG984xv2kEMOKYKgvNCf7/vWGFPM78+/"
                "v70BXdkB5nTdSABM3pYnvPItP+5POeUUu3jxYpIAAAAAAKamhx9+2B577LFFsK4xAni1BUVlB4zTadOo"
                "IHNrQf1YKyyQAOj85vu+vfTSS217XYA8IRCGIYkBAEBHsE4tAGCLms2mdRxHvu+bjRs32tmzZ5uNGzfa"
                "j3/84/r0pz+tLMskSdba4v85Y3iLmSzGmOL5tdbKWrvN57v959s/TlVTrf2u6ypNU+2///765je/qec/"
                "//kKgkBRFMkYI9/3OWEAAJOONxsAwBZFUWSzLJPjOPI8T9dff70++MEPauXKlZJaQWUYhnIcR2majvhd"
                "EgCTY0cDX9d1x/z9qRZI56Ziu4MgUBzHyrJMH//4x/We97xHlUpFWZapVqtxwgAAJh1vNgCArQrD0K5e"
                "vVrvfc979f0ffL8IWCQpTVN5nqc4jjf7vZmQANienvfJ3Lfv+6rVavJ9X8PDw1v9+TAMi98b/ThT0VRt"
                "dxAEklqvx4tf/GL913/9l4466ihFUaQgCKb/SQMAKBVvNACAEcIwtEmSaNasWUaSvvjFL9rLLrtMg4OD"
                "xXBzqfwArMzAeyz5EO8gCIpREZVKRUEQyHVdDQ8PK03TInniuq6yLJPneUrTtOihnz9/vvbee2/19vbq"
                "BS94gfbZZx8NDg5qzz331N5776299tpLkhTHsfr6+jRnzhz5vj+ibWO1MYoiNRoNDQ4Oql6vK8syrV27"
                "VsuXL9eaNWtkjNGf//xnPfjgg1q3bp08z9Pjjz9eDFGP41i+76vRaBRJH9d1i31nWaYoimStleM4I/7O"
                "SqWiKIom8FXYeWUfv+0uu+wyXXHFFcVUGkYDAAAmC28wAIAxrV692r7rXe/SddddJ+nZIeSSNhvuX4ay"
                "Rxh4nqckSYpAt1arKQzDEXPy29tojNH8+fO1zz77aP78+TryyCP1vOc9Tz09PTryyCM1f/58JUmiIAjU"
                "19dXBNOjH8cxjowzsgbA6Pn9juOMaGv+9fbHSZPWa5jZrBhNkGWZ0jSVY1q/HyexwjDUihUrtGzZMj34"
                "4IPFdtddd6nZbI7YnzGmCPhd1y2en/bnqVuUnQDwPE+SikTKoYceqm9/+9s67LDD1Gw2SQIAACYFby4A"
                "gBE2bNhgP//5z+tTn/qU1q1bp2q1qkqloiRJlKapkiSRVH4AVWYCYKwifJVKRY7jKIoiOY6jI444Qkcc"
                "cYROOeUUHXHEETr88MPleV6x5bUVms2mNhVaLB4rfxxjTNErnGXZiP1Wq9UiuM5HHowO/NvFcSxrbZG8"
                "yR+r/THzoFRSkQxob2serNbrdYVhqFWrVukP9/xBD/7xQd1www16+umntWHDBllri2khxpgi+C87adOu"
                "7OM35/t+MTIkCAJ9+tOf1jvf+U7FcUxxQADAhONNBQBQWL9+vT377LP1hz/8QfV6XdKzQ9vzQLFb5pCX"
                "HUzmPe/ValW+7+uFL3yhjjvuOB177LE69thjtddee43Zxjxor9frRdCeF4dzXbf4HWOMms2mrLUKgmCz"
                "x2p/LbI0K3ryRxv9e3nvfs6ttEZ2xHFcJADyKQxSKykQhmERoIZhqCAIZDOrzGZyjCO34hajH1auXKmH"
                "H35Y9913n373u9/ptttu08DAQDFaoFuUnQBof/08zxsxTeJlL3uZfvCDHxTHA4kAAMBE4c0EACBJ+vGP"
                "f2zf+ta3atWqVXJdd0SANFaw1A0B1GQ8XntQ1rZEW1G93fd9Pfe5z9VZZ52lF73oRTrttNPU29sra61c"
                "x5XjOjvUtm0lVrZ3mb+tPXb7Y27r8caaNtD++fa2b3BwUBs2bND//u//6tZbb9Wtt96qFStWjBgVYK1V"
                "T0+Pms2ment71Ww2lSTJpB5jZR+/o41+/mbNmqVrrrlGf/WXf6XMZiQAAAATgjcTAJih6vW67enpMWEY"
                "2g9+8IP67Gc/q2q1WvTwthdt65bCf+0mMgGwpb+rWq0qTVPttttuetGLXqQzzzxTL37xi7X77rurUqkU"
                "c97z9uxMm6Z6AmCs34/juFhCMp9GMDQ0pHXr1umHP/yhbrzxRi1evFgbNmwopj3kIyscxxlRdHKiddOx"
                "PJY8MXLeeefpy1/+subMmWPCMLSSWC0AALDDeAMBgBkqiiI7MDCgM844Q0uXLm0Vf9tUvT0vaJeb7gkA"
                "ScXc+yAI5Hme9t13X51xxhk655xzdNxxxxVF/3zfL4bmt1fBn4j9b+3zqZYAyKcwZFmmSqUia608zxtR"
                "pyDLMj3zzDO688479dOf/lQ33XSTli1bVtRFyIPgyTjuuulY3pJ8tYV58+bpJz/5iU488UTu2wAAAACM"
                "30033WR7e3utMcb6vm8lFZvjONZ1Xes4jnUcxxpjrDFmxM+UveVtmqjN9317xhln2K9//et2+fLlttls"
                "2lyWZTZNU5umqY2iyE6GLMtGbPn+8m3090dv2/PY43m8Lf3clto7emt/nsIwtGEYjmhTo9GwjUbDJnFi"
                "0zQtvnbvvffaT3ziE3a//fYbcRxO9Otd9vG7rc11XVur1azrulaS7enpsd/4xjdsvV63+UgAAAAAANiq"
                "gYEBe/nllxfB/eggP9+29X11eQLA9/3i76hWq7a/v3+zx+jp6bHnn3++veaaazYLuLcVgE+2bQXY423P"
                "eB9vZ//enX28KIrs4sWL7aWXXmoPOeSQIhDON9/3reM4O5wQKvv43ZHjW5K98MILbb1et5JEIgAAMF4M"
                "JQOAaSwMQxsEgck/DgwM2Ne+9rW6+eabi+X8cnYbQ85Hf3/05522PVMAjDGqVCqqVCrFqgZBEOioo47S"
                "RRddpDPOOEMLFy4csVTd9u5vslchGO/zu71D+nfUeP/ebe1vex4vf4yBgQE98sgjuvbaa/XTn/5UDz/8"
                "sKIoKqZl2E11AyayfWUb/ffkRSkl6dhjj9UNN9ygXXfdleKAAIBx4U0DAKa5MAyt7/v605/+pLPOOksr"
                "V64s5li3m04JgPa25XPJFy5cqLe+9a161atepf33379IDhhjiiX4xrM/EgBbt7MJAGutsjQrVlXIP280"
                "G/rtb3+ra665Rj/72c+0du1a+b6vMAzH1cayj99t2dL5lz8Xc+fO1f/8z//o3HPP5V4OAAAAQCv4t9ba"
                "G2+80c6ePdsGQWCr1ar1PG+LQ/u3NgVAXTA0Ot+2Z4i353n23HPPtT/60Y+Koef5nPMkTmwYhsV8daYA"
                "dNcUgPx5zx8r/1oURTaJE9toNOwTTzxh/+3f/s0edthh2z30vxuP5e05vvOv+75vPc+zkmxvb6+98sor"
                "bRRF3Z3NAAAAADDx8kCg0WgUAcG///u/W6lVVGyswn7bkwDoxoApn+OfB0Se59larWZ937cHHXSQ/dSn"
                "PmWXLVtmkziZlMAYnbWt1+O2226zF154oe3t7bW+71vXdW0QBGMG1t16TI9u51iJi/yczI9713XtBz/4"
                "wSIJQDIAAAAAmEHq9XrRU/qqv35VEQxtKQGgrQQc3ZwAqFarmxWBO/XUU+0Pf/jDzar1by0JQAJgatie"
                "16PZbNqnnnrKfuxjH7O77777iIKQo4sGdvu2rQRAtVotPvc8z77xjW+0w8PD1lrLKgEAAADAdNdsNoub"
                "/tWrV9sXvvCFI4LkLVX11xYCjqlQNd1xHFur1ezLX/5y+7vf/W5EAJTESRH4j16CbjyBJQmA7rA9r0cU"
                "RTYMQ1uv120URfbqq6+2hx566Ijj13GcMUcGdNu2rSk57X9PPvrlzDPPtE8//TTBPwAAADBT3HnnnXbP"
                "PfcsgghJNgiCaZcAqFar9q1vfat98MEHi7ni1rZ6+/NAMIkTW6/XGQEwDWzv65GmqW00GsXHer1ub7nl"
                "FnvcccdttpRgN2/bSgBUq9XiPAiCwNZqNVutVu0BBxxgn3jiCZIAAAAAwHRVr9dts9m0N998s507d+6I"
                "of7bCvy3tJUd/OcBTvvmuq6dM2eO/bu/+7sSQ1F0uzwp0F7E0Vpr7777bvuGN7yhqBmRH1O1Wq3rpgds"
                "b1HDfPM8z/q+b6vVqp09e7b99a9/baVWIdCBgQESAgAAAMB08t///d9FL2A+33m6JADyedzvf//77caN"
                "G0sOLzEV5aNBGo2Gve++++y5555bHGOu63ZdjYDxJgDa6wHkf8s111xD4A8AAABMJ81m037mM58pghhj"
                "zJgjALp9SP/orVarWak1feGiiy6yK1assNa25vO3D/kHtlez2bRRFNl6vW7DMLS/+c1v7Ctf+Urb09Nj"
                "gyDoqiTAjiQA2hMB2pTYuOSSS2wYhra9RggAAACAKajZbNoPfehDRRGw7Rn63y0JgO0JtC688EL75z//"
                "uQj48yJ/wI7IV4dI4sQODAzYer1u6/W6/eUvf2lPOOGErkoC7EwCoH1KgCT7qr9+lWV5QAAAAGCKaTQa"
                "tv3jVVddNSKg3tlh/53cRi/h1/69E0880d51113W2mcr+FOEDztra0UEBwcH7be+9S27cOHCEVMD2pfg"
                "6+T5sbMJgPYpAZ7n2Te96U1FcUxGAwAAAABTRLPZtFmW2U996lPW87wR64FPpQRAvrUnAmbPnm1vuukm"
                "G0WRzf/O9gr+JACwo7a1ikBeLHDDhg323//93+28efOKHnTP86ZkAqA9EVCtVu3RRx9th4eHCf4BAACA"
                "qWB4eNiGYWi/8pWv2L6+PiupmPc/FRIAo5c0y5dl8zzPfuhDHyp6+/OALYqiIgmQpikJAOyw7VlGsNls"
                "WmutjaLIPvLII/b1r399kQjo9BKCE5kAMMYUSwWecMIJ9qmnniIJAAAAAHS7KIrsJz/5yaJAXj7XV5p6"
                "UwDy7aijjrK//e1vi0Btw4YNIwK3RqNhkzhhCgB2yvYkAPJaE4ODg7bZbNpms2n/8Ic/2GOPPbbjowAm"
                "OgHgum4xpWG//fZjGgAAAADQjcIwtJL0zDPP2Msvv3xE8N8e2G8tAdBNRQDzQGT27Nn2+9//vm00GiOG"
                "YI8V4BPwY7KNNR0giZNiu+aaa+yee+5ppdYSlT09PcWogLHOr27c8lE3ruvaOXPm2GXLlllJqtfrJAMA"
                "YIYwZTcAALBlzWbTVtyKojjSBz/4QX35y1+WMUZRFG32s8Zs/ZJurd3q553g+76stbr00kt1+eWXq1ar"
                "KcsyBUGgLMskPft3bOvvASbSts4HY4yefvppffKTn9R///d/K4oiVSoVVSoVhWFYyvm0o4wxcl1X/f39"
                "evDBB7VgwQLV6/Xi60EQcPIBwDTFBR4AulQYhjbLMmVZpr/927/VN77xDfX09KjZbI4ZbHR7AsB1XR10"
                "0EH64he/qBee9EJlNpPnecqyTMaYoj0kAFCGbZ0PWZrJcR1J0g033KB3v/vdWrlypVzXlTFGcRx3opkT"
                "xlor13W1++6761e/+pUWLlyoOI5ljFFPTw8nHwBMU07ZDQAAjC3vhfvIRz6iH//4x6rVapKkLGsFzlPN"
                "FVdcoSVLluiFJ71Qw/XhIuByHEfNZrPk1gHbFoahjDE699xzdeedd+q9732vJI05ImcqyLJMTz75pE46"
                "6SQ98MAD8jxvSo1kAAAAAKaFRqNhoyiyn/jEJ7aryN94tsmsBZAv6VetVosl1E488UT7wAMPbHHO9ej5"
                "1xT5Qzfa0vH50EMP2aOPPrqoy5Gfr2XP999aHYD2La8J0N/fbxcvXmyttTavOwIAmH4YAQAAXaLRaFip"
                "tdSf67r61re+pQ9/+MPFEPmpwHVd9fT0KI5jpWmq97///brtttt06KGHbvF3LD2OmKLiONZBBx2kJUuW"
                "6CMf+Yh6e3tVqVTU29tbdtPGLYoinXbaaVq0aFHZTQEATKKpcUcJADNIGIb25z//uV71qlcpjmM5jqMs"
                "y+Q4E5OzHR1wT2QAnicq+vr69MUvfFGvPu/Vcl13zLZva79TJemBmWGs4zVLM8VJrCAIZIzR0qVLdd55"
                "52nVqlUaHh4uoZXbNvq8yutv9PT0aGhoSPPmzdP999+vXXbZRb7vcxICwDTDCAAA6BLDw8NWkh566CG9"
                "9a1vLQpyZVmm/v7+spu3XRzH0SmnnKK77rpLF7zuAmVZJpvRw4/pJw+kq9Wq4jhWlmU67LDDtGTJEl1w"
                "wQUlt278hoaGFASBGo2GDjnkkClX1BAAsH3I7AJAFxgYGLDValXr1q3TgQceqKGhoSLAsNbKGLNZz13Z"
                "Q+fz5ITrusqyTLVaTZ/4xCf09re/XWmaFkULgZlg9Pn4ne98R5dcconWrl2rarVaFLpsP6/bdXrEy1jX"
                "k/Y2veAFL9Dtt99efM5oAACYHhgBAAAlaTabxd12f3+/Wb16tY444gglSTIieO7WofDGGDmOI8dx9IIX"
                "vEAPPPCA3v72tyvLMgVBUHbzgI7Kk3T5dt555+m2227TySefrDAM5XmeXNedMpX27777br3lLW9RkiRT"
                "or0AgO1DAgAASlKtVovIvl6v2zPOOEPr1q2TJDUajdLatb0cx5Hv+7rwwgt10003aZ999lGlUlG1Wp2w"
                "egXAVBVFkQ455BD97//+ry6//HIFQSBrrdI0leu6ZTdvhLEC/DRN9f/+3//T//k//2fKLnMIAAAAdJ1m"
                "s2nPP/98K8n29/cXS+pta/muspcTW7Bggf3qV79q6/W6zbLMhmFowzDs1KpsQFeLosgmcWLTNLXWWnvL"
                "LbfYefPmbXH5zDKXAxxrSdBarWZd17WS7L//+7/b9hFLAICpqzvHlQLADBBFkfV933ziE5+wH/3oR7fZ"
                "6192DQBjjFzXVZqmmjt3rn7xi1/osMMOk+M48jxPWZaNaGe3Tl0AOmH0+WmM0cqVK/W+971P3/nOd4pz"
                "KQgCxXFcyvncbqz9G2NUqVRkrdXdd9+tI444wjQaDVur1Ti5AWCK4gIOACWJosh+61vf0pvf/OaioN7W"
                "lJ0AyNvwghe8QDfccIP6+/sVBIHSJFWSJvI8b8x2kgjATDT6/MxXCjDG6HOf+5z+8R//UY7jqNlsFl/v"
                "pPFcT4wxeu5zn6vbb79de+yxh6IoGjGFCQAwdXDxBoCS3H///fbYY4+VtXa7egDLTgAYY3TuK8/V177+"
                "NXme1yoAaBylWSpJch1Xxtl8tQISAJiJRp+f1lpFUSRrrYIg0M9//nO99rWv1cDAgKTuWAVga6y1ev7z"
                "n6+bb75ZPT096unp4cQGgCmIKk0AUJJXvOIViuNYURRts/e/G3zuc5/T967/nlzXVaPRkOd5StJWhfBK"
                "pSLjEA8AW+I4jqrVqmq1mpIk0Zlnnqk777xTe++9dzF6ZlvspqX6yhj9I0l/+MMfdOGFF5aybwDAxCAB"
                "AAAdFEWRHR4etqeccop9+umnN5s3Xybf92WMKQJ63/dVrVbV19enb3/723r7xW9XmrTmLPf398taK9/3"
                "FQSBHMcplj/Ljf4cmElGLwvYzvd9ZVmmgw46SEuXLtVxxx1XBPb5OTj6d8caUTCRCYHR7R2r/ZVKRb/4"
                "xS/0xS9+UZIUhiGFAQFgiiEBAAAdEkWRTdNU//Iv/6I77rij65b6i+O4WJ4sTVPFcayenh7dddddOv/8"
                "80tuHTD15cF6lmWyWWvqz7x583T7bbfr8ssvl+d5qlQqCoKg7KaOKR+xdNlll+m3v/2tLWskAgBgx5EA"
                "AIAOsdbq29/+tq688squHPKfZZniOC4q+p9xxhlauXKlDjjgAKVJ2prf74zdowlg2/Jzx3EcuRVXnucp"
                "jmMZx+jDH/6wrrrqKlWrVUVRVHZTx9R+3p977rl68sknS2wNAGBHcAcHAB3y0EMP2ec///lFIbDxmuwi"
                "gJVKRWmaKssyXXDBBfrc5z6n/v5+eZ43Ypjxlor8jbXsGYAti6JIvu9LkprNpryKp3vvu1cvfelLi+KA"
                "krZrmP94z7fx/Hy+7/Y2+L6vY445Rj/72c80Z84cTnYAmCIYAQAAHbBhwwZ74okntorlbZrjO9FzeMer"
                "fc6xMaZYpuyyyy7Ttddeq3nz5m1xab+xbG3OM4DN5cG/JFWrVTmuo8MPP1yPP/64dt99d7muq76+vuI8"
                "LUu+7/bzO4oiLVq0SP/wD/+ger0+4gIWRRFzAwCgS1XKbgAATFdhGNogCMzw8LB9/etfrziOlSRJaRW8"
                "t8QYozRtLeX35S9/WW94wxuUJqnciltyy4CZxRgjz/PU39+vhx56SEcddZSWLVsmx3G6ctpQpVLRF77w"
                "BR111FHF9U6SfN8nAwgAXYoRAAAwSfJesy996Uu64YYb1Gg0dnj4vzTxVb8dx5HrunJdV47j6Lvf/a7e"
                "9KY3yRgzZvBPlX+gM4wx6u3t1e9+9zsdffTRXbVaSLskSeR5nt7znvfo4YcfpucfAKaA7nonAYBp5k9/"
                "+pM98sgj1Ww2R3w9nwYw+mudZIxRlmVyHEff+ta3dN555xVtGGsEQNntBWaSfNh/FEW68MIL9a1vfWur"
                "Pz+ZNQDy9oz+/Xz0kOM4OuCAA7Ro0SLqAQBAl2MEAABMksHBQXvWWWcVwX/7PNqxjFUXYKLX+Z41a9aI"
                "tcZrtZp++tOfFsv85fty3M3fHpjjD3ROfo75vq9rr71WL3vZyySpKMy5s7Z1vdnW9ae9hoi1VsuWLdPb"
                "3va2zeoBAAC6CwkAAJgg7Te+jUbDvvWtb9UjjzwiSeMqpjdZenp6lCSJgiCQMUZz5szRT37yE730pS/d"
                "bIQCgO5y/fXX6/TTT1ez2VSl0h0lnNoTA2EY6rvf/a6+/OUvl9giAMC20IUDABNoeHjYzpo1y9xxxx32"
                "pJNOUk9PjxqNhiqVipIkGfGzO9urvyNDeIMgkOu6iuNYX/ziF/WWt7xFYRjK87wtLu8HoDvEcayzzz5b"
                "v/zlL4vCnbmyz1djTFFP5I477tAxxxzDBQQAuhAXZwCYYE8++aQ9+uijtXr1agVBoDAMJW1+gz7ZCYDR"
                "dQbyofuO4+hzn/uc3v72t0tq9dy1L0e2vY8PoHOazaYcx1GSJDrhhBN0//33j/h+2edrXlNEkvbaay89"
                "8MADmj17NhcRAOgyTAEAgAmSV8B+29veprVr10pSEfxLE1/Ff1vy+bmO48jzPPm+L9d1ddVVV+ltb3tb"
                "8XP5lADm+APdq1qtqlKpqFKp6K677tLee+8tqVUjwPf9Mc/hrW0TrX2ZwieffFKXXHKJJKnZbNowDKkL"
                "AABdggQAAEwQ3/fN17/+dXvjjTd2xRxda62yLFOapkU18b/7u7/TRRddpKGhobKbB2CcHMeR7/vyPE83"
                "33yz+vv7FUXRZtOLusF3vvMd/b//9/9stVo1QRCQUQSALsEFGQAmyFNPPWWf//zna/Xq1R3Z37Z68RzH"
                "UaVSUZZliuNYl156qT71qU8piiK5jrvZMn8Apo4sy/Too4/q2GOP1cDAgBxnfH06Ez0KafTjua5brA6w"
                "9957c78JAF2CEQAAMEEuuugiDQ4OqqenpyuG0HuepzAM5TiOzjvvPP3bv/2bms2m0jRVmqXbfgAAXStJ"
                "Eh1wwAG69dZbVavVym7OmHzf1ytf+cqymwEAaEMCAAB2Qr1et1EU2Xzof6PRUL1eL7tZklRUCd9///11"
                "zTXXyPd9VatV1Wq1MYv+AZg6PM+TtVaHHHKIvv71rxdJx9G1RjpVc2SsGgPNZlN33XWXPv/5z1MDAAC6"
                "RPldVAAwxa1du9bus88+ajQaHd3vtkYZeJ4nx3F03333ac899+zaXkIAOyYP7JvNpv7zP/9Tl19+uTzP"
                "UxzH21zWc7KTAtbaoi2S9Oc//1kHHngg950AUDJGAADATnrjG984otp/N/n5z3+u/ffff9zzgwF0vzyo"
                "r1ar+sAHPqAzzzxTWZYpCIKSW9aSJIk8z5MknXXWWcXXWRUAAMrDHSEA7ITPfe5z9tZbb5Xrdl9BvSuv"
                "vFIvPOmFajQaXRMQAJhYeRLA933deOONOvjggxVFUcmtarHWKo5jeZ6nFStW6N/+7d+sJLEqAACUhwsw"
                "AGynZrNpq9WqkaQoiuyaNWt0yCGHqNlsFsvsddKWhvhmWaYPfvCD+uQnP9nR9gAoT5ZlMsZozZo1Ou64"
                "47R69eoRI5M6XZh09BQDz/NkjNFvfvMbHX/88dx/AkBJuAADwDg0m01rjJG1VmeeeaZuvfVWGWPkOE5R"
                "dK9Txrqh931fJ510kq6//nrNnTu3o+0BUJ44jpUkiYwxevDBB/WSl7xEQ0NDMsYUyYFOGmtZwDRNtf/+"
                "++vee+9VT08P96AAUAKmAADAOFSrVRMEgfnZz36mW2+9Vb7vq1KpdDz4H4u1VrVaTddeey0F/4AZxvM8"
                "+Z4v13V11FFH6Tvf+Y48z1OWZV1RAyRNUzmOo0ceeUQf+9jHym4OAMxYZF8BYJzWrl1rDzvsMK1evVqS"
                "5DiOsizreDvy5bbynjZrrRYvXqxjjz1WzWZT1Wq1420CUK58zr0kXXbZZfqP//iP4uudNNYUgCRJZK2V"
                "4zh68MEHdfDBB3MfCgAdVn5KGACmmA984ANas2ZN8XkZwb/USgDkxQettfrc5z6nY489VmmSEvwDM1Qe"
                "/EvSRz7yER1//PFFsrBSqRQjhfKvjXcbzVo75jZaHMfF17Ms06WXXjp5TwIAYIvIvALAODz44IP26KOP"
                "VpZlpVfaDoJAcRzLdV0de+yx+s1vfiOpNdQ2TUkCADNZvV5XrVbThg0b9LznPU/r1q1TFEXKskyu644Z"
                "pG+P0b+3o4/jOI6+/vWv6w1veINpL7AKAJhcXGwBYDs1Gg374he/WHfdddcO3/ROJN/3FUWR+vv7dffd"
                "d2u//fbT4OCg+vr6ym4agC6QXw9+97vf6ayzztLAwICyLJPv+0qSZIcec6ISAJLU09OjJ598UnPnzuV+"
                "FAA6hCkAALCdvve97+mee+5RpVKR7/tlN6fwla98Rfvtt5+stZo1a1bZzQHQBfKpQHEc68QTT9T73ve+"
                "4roVRVFXJDHjONa73vWuspsBADMKGVcA2IYwDG2j0dBhhx2mp556StVqVWEYdnTufz73dvRN+2WXXaYr"
                "rrhCklSpVMb8HQBIk1QnvOAELVmyRD09PWo0Gjt0jZioEQC1Wk1pmiqKIt1666069dRTuWABQAdwsQWA"
                "7fCud73Lfu5zn5PjODLGyHGcjlfVllo3zc1mU57n6fDDD9edi+5UkiZjjkggAQAgF0WR/vSnP+mkk05S"
                "HMcKw3CHlgecyCkA+TSmY445RkuWLDFRFFnf97lwAcAkYgoAAGxBGIZWku6991779a9/Xb7vK8syWWtL"
                "Ca7b1/SeNWuWvvWtb8mttIp57eh8XgAzg+u4Ouigg/T5z3++9AKmOWutPM/TkiVL9MMf/pDgHwA6gAQA"
                "AGxBEARmeHjYXnLJJRocHFSlUpExRlmWKU3TjrcnTVOFYag0TfXRj35UBx10kBqNhqrV6oilvwBgtMy2"
                "iv+95jWv0RlnnFF2cyRJSZIUK5lcdtllGhwctM1ms/ziBAAwjZEAAICt+Pa3v61f//rXMsao0WhIUpEE"
                "6PQogLz3/5RTTtHb3/52Sa0pAbltrdcNYOZyXVdpksp1XP3kJz/R3nvvXSwJaIyRtXbE1gn5ftI01R//"
                "+Ef9+Ec/luM4IgkAAJOHO0QA2IK1a9faI488UqtWrZLneQrDcMT3y6ii3dfXp9/+9rc68MADFQRBx/cP"
                "YOrKr1lZmul7139Pr33ta4uipqNtKYk4kTUA2jmOo3nz5umJJ55QT08P96cAMEkYAQAAW/DZz35WK1eu"
                "VJqmajabZTdHruvq0ksv1WGHHUYPP4Ad5riOXv2qV+v1r3+9siwbMZKoLK7ras2aNfr85z9fdlMAYFrj"
                "DhIAtmDBggV2zZo18n1fSZJMWs/X9jrxxBN10003KQgCGWPGrPwPAFvSfs2K41hr167VwQcfrCiKtrmq"
                "yZaWIp3o6+A+++yjP/zhD5o7dy73qAAwCRgBAABthoeHrSR94AMfsBs3bmzNm03TUob7+76vWq0mY4yq"
                "1aquueYaVatVBUGw2XzdMtoHYGpprxHSbDa155576vrrr1cURcV1JK8HMNro68xEX3ccx1Fvb6+efvpp"
                "ffWrX1UURXbjxo22Xq9zcQOACUQCAADaeJ6n5cuX26985StFpf8sy0ppi7W2KDZ4ySWXaJ999imq/dP7"
                "D2Bn9Pb2Ko5jnXTSSXr5y18uz/PU09NTBPWdTjBmWaYoipSmqT772c9qeHhYjuNQDwAAJhgJAABo4/u+"
                "+c///E9t3LhRUnnBv9TqrUuSRPvvv7+uuOIK+b5f9M5RAwDAzvI8T7VqTV/5yle0YMEC1ev10kYT1Wo1"
                "RVEkY4wee+wxffWrX1Vvb6+iKGIEAABMIO4gAaDNihUr7AEHHKAsy7Y5J3Yib5S3NOw2CALdcsstOvro"
                "o+U4zogkwFiPAQDbK7/OBUGgq6++Wn/7t38rz/OKKQHtRl9fJvr653me0jQtRl7NmzdPy5YtU5qm6u/v"
                "5+IGABOEEQAAIBW9TB/72MfUbDaLm9CtaZ9Pu7Nb/nhSqxp2tVqV4zh65zvfqeOOO27Mon9jPQYAbI88"
                "gPd9X9ZavfnNb9ZRRx2lKIpUrVY7fn2J47iY8mSM0cDAgL7//e8T/APABOOiCmBGC8PQBkFgJOnRRx+1"
                "Rx99tDZu3FhKQG2MUZZlCoJAYRhq9uzZeuyxx9Tb2yvXdTdrE0E/gB01VjX/3/zmNzrllFPk+35HR0BJ"
                "m1/Pent7tXDhQt15553UAQCACcQIAAAzmrVWjUbDStKHP/xhNZtNSa2K1J3UfvObJIl839eVV16pWq2m"
                "OI473h4AM0uapnrxi1+s17zmNYqiqOzmKIoi3X///frpT39adlMAYFohowpgxqvX63bjxo068MADlaap"
                "XNfV8PBwx9tRqVQktYbCHn744br77rvlGEeO64w5758RAAB21Fg9+I1GQ2vXrtVznvOcbV5fJnsEgLVW"
                "juPopJNO0i233KJ8pBYAYOfQpQRgxuvp6TFXXHGF6vW6wjAcUQm7k8tgSa3g3/M8felLX5JjHBmH+f0A"
                "Jt6W5vjvscce+shHPqJqtaparVasOjL65ya7NkBe9HTJkiVavHjxpO0HAGYa7ioBzFiNRsMmSaIkSbTv"
                "vvtqYGCg+F57AiA32YF4fqP9hje8QV/84hfle/4We/870R4AM0e+BJ/neRocHNTuu++uZrOpLMvkuu6Y"
                "18SxPt9Ro69ntVpNrusqiiKdfvrp+slPfmLaa7YAAHYMIwAAzFhJksjzPH32s5/Vhg0bym6OpNa63B/7"
                "2McUBAG9/wA6xvd9eZ6nOI7V29urK6+8UlmWyXEcua7b8fbU6/WiJssvfvELLVmyhOAfACYACQAAM5a1"
                "VoODg/rc5z5XfN7J4f6jGWP09re/XQsXLlSSJEXwX1Z7AMwcWZYpyzJ5nqcoivSmN71JBx54oKRWsrTT"
                "XNdVkiSK41iu6+prX/tax9sAANMRCQAAM5bv+/rhD3+otWvXbtbD1YlEQL6PfB3u3t5e/dM//ZOk1kiA"
                "PAEweq5up9blBjBz5NeV/JpUrVb1f//v/y0SA52WT4mSpDAM9a1vfUvDw8NWkqIoIisKADuIBACAGStN"
                "U33kIx+R67pK07TjIwCCIBjx+T/90z9pzpw5ajabBPgASjU4OKjzzz9fBxxwgBzHKX0k0jPPPKOf//zn"
                "iqLI+r7PBRIAdhAJAAAz1s0336yVK1cWQ0w7LQxDBUGgMAzV29urt73tbcqyTEEQlH6zDWBm6+vr06xZ"
                "s/TFL36xaxKSn/zkJ+UYpxgJAAAYPxIAAGasq6++WpLU29urSqVSShvyZf/e//73q6enR1mWKY7jrrnh"
                "BjBzpWmql770pTr00EO3uBpJp1QqFf3ud7/TI48+Isfh9hUAdhR3mABmpKVLl9pjjjlmxNc6fXObz3Gd"
                "PXu2nnzyyWIUgud53OBugbVWSZLIWivP85SlmTKbyVqrLMtUrVYVx7Ec4yizreXLtjR8mSTL1JfPTXcc"
                "R2EYSpIqbkVJmhTV7LMsU5qm8jxPaZLKrXR+tM9UlU+JuvPOO/XiF79YnuepXq9Pyr5Gn4+jP/c8T1mW"
                "6W//9m/16U9/WkwDAIAdwx0mgBnp2muvLbsJqlarstbq3e9+twK/VQ/AcRwC0y3Ig/88ELDWanBoUAMD"
                "A8qyTMPDw2o2m0rTVpDXnkiJ47jk1mMyGGOK1zg/b+Ik1tDQkBzH0erVqxWGYVHFPg/+0yQtp8FTTF4Y"
                "8Pjjj9cLX/hCJUmiarUq3/c73pY4jhXHsb75zW+q0Wh0fP8AMF1wlwlgxmg2m7ZarZpnnnnGHnjggVq/"
                "fv2I73d6BEClUlGtVtPjjz9e9FTS+79lcRxr48aNuvnmm3X77bfrF7/4hdasWaN6vS7P87Trrrtq9913"
                "1/HHH6+zzjpLL3nJS+Q4jnzfVxzHm03zINEydbWfq9ZapWmqO+64Q9dee62WLFmiZcuWaf369arVajLG"
                "aNddd9V5552nd7zjHdp9991LCWCnMmutli5dqmOOOUbGGFUqlWIkzkTZ1vlorVWtVlOj0dB3vvMdnX/+"
                "+ZzAAAAA2LIwDK0kfe1rX7NBEFjHcUZsxpiObx/+8IettdYODw/bKIpslmUWdszn4bLLLrOzZ8+2ruta"
                "SdbzPBsEga1Wq7ZWq9kgCGwQBFaSrdVq9qijjrJf+tKX7ODgoM2ybLMNU1sURbZer9uvf/3r9uijjx5x"
                "HnueZx3HKY4RSVaS7e/vt6effrr93ve+V3bzp5wkTux5551nJdnZs2dbY0zxvE7Etq1rpSRbrVat53n2"
                "jDPOoAggAAAAtq1er9sjjjhiu244J3qTNCIY6evrs81m04ZhaJvNpk3TtOx7/K6RxEkRpP/+97+3/f39"
                "RXCnUQHD6ESO67rWdV3b09NjjTH25JNPtqtWrSoeF1Nb/houWbLEHnTQQdb3/TGD0bHOv/bt2GOPtatW"
                "rbJZlhXnXvv/MVIYhnbJkiUjkqejn9OJ3Lb1+g0ODpIEAIAdwDhTADPK3Xffrfvuu6+UZf+CIFAcx/J9"
                "X67r6v3vf7+CIJDv+/I8jyHpm6RJqjRLZYzR/fffr9NPP72Y5283FU7cHvV6XUEQ6De/+Y2e97zn6fe/"
                "/30xB9yyzOKUlBf6u/322/Wyl71MjzzySHH+bEs+nz3f/vCHP+iwww7T73//e9msVewujuOiXgBG8n1f"
                "Bx98sA455JDSVk1p99WvflVSa2pXFEWc0AAAANjcW9/6Vuv7filD/iUV+/Y8zz7++OMl9+l1nyRObLPZ"
                "tPV63d5999127ty5xdDfLQ053tIIANd1i95K13VtX19fMfS7Xq+X/JdivPKe/+9+97u2VqsV00DGOia0"
                "HSN88qkkc+bMsT/4wQ9so9Gw1rZ6uqMoKvNP7Ur5qJyvfOUrVlLx/JW1HXHEEbZerxP4AwAAYGyrV6+2"
                "/f39xTD8MhIArutaz/PsOeecY9M0LYKOmS7LMpvEiQ3D0NbrdTs4OGh32223EUP5tYVAYEsJgPx38o89"
                "PT12/vz59u677y77z8UOiKLIXnfddUXwn7+uW0oCbO1czI+T/GOtVrO33XabTeLERlFkh4eHy/5zu1KW"
                "ZTYMQ7vnnnuWngAIgsA+9NBDVpLWrl1LIgAAthNTAABMe/nw0FtvvVXDw8NyHKeUSvue5xVV/j/0oQ8p"
                "SZKiGrndtN52+zaTGGMURqE8z1OtVtPxxx+vVatWKU1T1ev1rT4fYz13+c/n0wWMMYrjWIODg3rlK1+p"
                "tWvXFr+L7mWtVRiGajabeuqpp3TJJZcoSZJiCo8xRkmSbDa8f2vTRPLvtb/2URTp7LPP1iOPPiLP89TT"
                "0zOjz8ex2E1TJFzH1cUXX6w0bS2lWNbUpTiO9bWvfU2SNH/+fMM0AADYPiQAAEx7+bzh//zP/5QkJUmi"
                "LMs63o5KpaIoinTiiSfquOOOU6VSkeM4BBibZFmmLM10+eWX649//OOEP34eKK5YsULvePs7lCaprLVq"
                "NpsTvi/svDAMW0vOuRVVq1Wdf/75GhgYULVa3a45/+PVaDT0ute9TmmSTvhjTwfGGLmOK+MYXXzxxapW"
                "q6pWq3IcR0EQdLw9WZbpJz/5iZrNJhdPABgHEgAApq1Go2Elqa+vz6xatco+8MADcl1XcRxPSgCxHe2R"
                "JL3//e+XJIL/UXp6evTEsif06U9/WtVqdcIfP++prFQq+v4Pvq8bf3Zj8T1eg+6TnxtuxdV1112nRYsW"
                "yRij4eHhIqk3kdI01dKlS/Xpz3ya42EMaZLKrbhK01R77bWXzj33XEVRVIyo6vRIANd1dd9992n58uUd"
                "3S8ATHUkAABMW7VazeS9QzfeeKPCMFQURXJdt5RK347jaI899tBLX/pSRVFE8K+RgXez2dTrX/96ZVmm"
                "OI4nZX9RFBXP/eWXXy6b2UlJNmDn+b6vJEk0NDSkD3zgA/J9X3EcT+p5Y4zRv/7rv2pgYGCzr890bsVV"
                "GIZF8vTiiy9WT0+PXNctZURVPp3qJz/5icIwnNkXUgAYBxIAAKY1Y4yazab95je/WQz1TtO0lMDbGKNX"
                "vepV6u/vlzFmxgf/OWutsizTb37zG/3+979XmqbF/OLt/f3253JLAWL+9XyO+EMPPaTvfu+7iuNYURRN"
                "yN+CiWMzK8/z9NWvflVPP/20kiTZrLaDtOXXe4uPu4XjxXVd+b6vgYEBXXHFFWMG/TO9JkD7UP+jjz5a"
                "u+22m5rN5qSMyNiWfCnCG264QWmayvd9sjQAsB24WAKYtvJeofXr12vfffdVGIYjbtw73atXq9X0pz/9"
                "SQsWLBhzHe3R7ZkJvY55MOU4jo499lgtXbpUxphxJQBy432+fN/XUUcdpV/96lequBU57sic+Ex4/rtZ"
                "mqSqN+o6+uijtWbNGg0NDUnafLrGWEmB7TH65/NebMdxNH/+fD3xxBMyxoyYLtT+OzP9+MiyTP/n//wf"
                "XXXVVWo2mx1PauYJm56eHt19991auHDhzH5BAGA7MQIAwLRljJHv+/rVr36lZrNZeq/dCSecoN132131"
                "en2HAtzpyBgjm1ktWrRI99xzj4IgUJqmRZX3yRTHse655x4tXrxYbmXy94fxcSuufvSjH+mRRx7p6JQd"
                "3/e1du1afec731EQBCNWGsCzms2mLr74YmVZJtd1O/78WGvVaDS0bt06/fznP+/ovgFgKiMBAGDaiuNY"
                "zWZTP/zhDzsSUG7LO9/5TmU2k+M4Y44AmGnyof+O6+iaa65prQKwqRe2EwmSfAWAa665ZtJqDmDHpUmq"
                "K6+8Un19fUUCb3umeuwo3/cVBIHiOFZPT4+uvvpqNZtNZWnG+TqGWq2mgw46SEcddVRpqwD09fXJGKOf"
                "/exnHd8/AExVJAAATFuzZs0yURTptttuU5qm271O+ERpn3M+Z84cnXfeeXJdV729vaWPRugG1lrZzGpo"
                "aEjXXXddseZ7p8yePVtSq0DkTJ7X3a2WLV+mP/7xjxoaGupIAJ7XgsiyTMPDw7rnnnu0YsUKRXEkm20+"
                "93+mHzONRkOO4+jCCy9UlmUdu662Gx4elud5+vWvf63169fP3BcDAMaBBACAaW3x4sVasWJFKcN3816x"
                "SqWiiy66qOP773Zpmiqzme6//34988wzHd//hg0bJElPP/20HnjggY7vH1v34x//WGEYFjUh2gvwdSLw"
                "HhgY0Le//W05jqMopkjkaJVKRVmW6RWveIVmzZpVShuyLFOSJFq/fr3uueceRVFkwzC0+RKwAIDNkQAA"
                "MK19//vflzGmlCGqeWX5IAh00UUXbTYCodMjErqN67pyjKPvfve7pVThdxxHQRAoiiLdfvvtHd8/tu6W"
                "W25RrVZTtVotpWaGMUbXX3+9PM8r5frR7XzflyTtvffe+qu/+qvS2pEnAb7zne8oyzIFQWBqtdrMu6AC"
                "wHYiAQBg2mo0Gvamm26SpFICTM/zVK1Wtddee2nfffft+P67neM4RaG3MhIg1lpFUaRKpaL8OGn/Hsr1"
                "29/+VgMDA6W9FtZaPfbYY1q3bp0ch9ul0dIklc1a59AFF1xQaluyLNONN96oer2uer3OCAAA2Are0QBM"
                "W0899ZSWLVumSqWinp6ejve4G2PUbDb15je/WbVabZv7n2kjArIs05o1a7RixQrNnj17myMktvX8jB4i"
                "vq0tl6apFi1apHq9PuKxOz3kfKaLokiNRkNZlumxxx7T4OCgXNft2AoAo4+vvr4+DQwM6JZbbim+L41c"
                "dnAmnKdb4lZcOa4jz/N02mmnad68eUXNk97e3o6357HHHlOWZerp6WEEAABsBQkAANPWL3/5y/yGUPV6"
                "veP7D8NQfX19euUrX0kAuQWLFy9WlmWljNDIXxNrrdatW6f77ruPYL9EeRX+NE111113FcP+y1oyM0kS"
                "OY6jH/7wh0oTlu0cizGmWNXk9NNPl+/7qlQqpVxvjTG64YYbJElRFHESA8AWkAAAMG1de+21MsaMWF6u"
                "k4Ig0F577aXnPve59PiPwXEc/fSnP1WWZR2t/t+uPQlw6623FtMCZuLrUbZmsyljjDzPKxIAjuOUcu5K"
                "rSr3cRxr8eLFGhgcKKUNU4UxRmeffbaSJFGapqpUKh0/h6y1uvnmmyVJvu9zAgPAFpAAADBt3X333apU"
                "KhocHCxl/0mS6NWvfrW8ildKj9hUsHjxYqVpWlovr/RsEuDee++VzaziOCYBUIIgCGSMkbVWixcvllRe"
                "73/O932tWrWqtATVVHLKKadowYIFkp4tENhpN998s9auXUvvPwBsBQkAANNKGIY2DEP74IMP2nq9rmaz"
                "KUmlFPGq1Wq64IILlGYpAeUYVq1apccff7x4bcqcc2+t1ZIlSxQnsWrV2oh1zWfqCI1Oy5/joaEhPfro"
                "o5LKLcaYz2NvNBq69957i69zPIxtr7320pFHHinXdTU0NFTKc7Rq1SotX7684/sFgKmEBACAacf3ff3i"
                "F79QGIbKsqy0Ct7Pec5ztMcee0hqJQMw0vr167Vu3bpiHnHZ1q9frziOlWZpxwrP4Vl5sJ8kidatW1d6"
                "LYY8iI2iSHfffXfp7el2juPoda97nTzPK2UEQL5U429/+1tqAADAVpR/xwUAEyQMQxsEgQnDsFgTuszA"
                "8vTTT9e8efPkOm5pbehmDz/8sOI4liRVKpWSWyMNDg7qqaeeohBgSfLnfOXKlRocHCz9dXAcR2EYynEc"
                "/fnPf5ZE7//WRFGkv/zLv1Rvb28pdTSiKJLneZst6QkAGIkEAIBpIw8WVq9ercWLF5feq3zaaacpyzK5"
                "FRIAY3n44YdVrVaVpmlXBNzGGD3yyCNFkMcygJ2Vn6+PPvpo1wXZt95664jPOR4253meent7td9++8l1"
                "O3/N8zxPcRxr6dKlpRWOBICpgAQAgGmjWq0aqTUEVOr8nHLHcYp9zZkzRyeddFLpSYhuE8dxMTXjjjvu"
                "KGo05CMB2nX69avX67r33nvl+/6YQ5hJCHTG+vXrSy/+l8sTQRs2bNDw8LAklbJk5VRRqVR09tlnF0m9"
                "TiZy0jSV7/tasWKF7r///o7tFwCmGu5MAUw7t99+uxqNRsf367quPM+T4zh69atfrfnz53e8Dd3OdV05"
                "jqM0TfXII49I6p7eVM/zWoUA41hpkhLwd1iapEqTVA888EDXjQCo1+tavXo1x8FWGGPk+75e/vKXl7L/"
                "fPlB13X1ox/9qJQ2AMBUQAIAwLQyODhob7vttlL2HUVRUezvzDPPLKUN3c5xHLmuqyzLui4B4Lqu/vjH"
                "P0qSkjRhFYASGMdo2bJlXTNyJn/dG42GVqxYIZtZjoctyIfdH3XUUZozZ04pbciX8Fy6dGkp+weAqaA7"
                "3mEBYIIMDw/r6aefVk9PT8f3bYzR8PCwfN/XS17yko7vv9vlAUL7VAmpexIA1lo1Gg1VKhUCvBI4rlME"
                "/t0yBaDdmjVrJEmO4dZpLPlr5/u+zjjjDEnq+HkUx7GiKNKSJUs6ul8AmEp4FwMwrTz00EMaHBxUvV7v"
                "eA9uHtQeeOCBmjtnbtcEtt0iDEOlSSuwW7FiRTH/v1sYY/TYY49peHh4s2NnrA0Ty1qrwcFB/f73vy+7"
                "KSPkr/cdd9yhOImV2WzMmhV41jnnnNOxc2T0eek4jlasWKFHH33USmJJQAAYhQQAgGnl6aefVpqmxVD8"
                "TqrVagqCQK9+9avluK3LK3PIRzJOKyhYtmyZkiQpuTUjWWuVZZmazWYpVczRCuaeeeaZrpkC0K5erysI"
                "AnmeJ8/zym5O18mLezqOo2OOOUZpmirLstKSZY8//rik1nndbDa5AAPAJt33DgsAO2HRokXKsqyUgDuK"
                "IllrGf6/Ba7rKk1bhd7Wrl3bdUt1ZVmmLMuKEQDoLMdxVK/XVa/XuzLAfuqpp4r/d9ux2w2CICim9+y7"
                "777ac889JXV+GkAuXw0mCAKTrxADACABAGCaufPOOyWplOHlWZapVqvphBNO6Lrh7d3A9/1ibnc39vDm"
                "iaNGo0ECoCQbN24slt7rNk8//bSiKFIURarX62U3p6tYa5Umz/b4B0Gggw46SI7jKMuyMZfVnGxL7lrC"
                "8H8AGEP33YEBwA5asWKFfeihh4rPRy/jNtHbaJVKRQceeGCRCGDO+ObyYf9//vOfS27J5vJ1yx955JGu"
                "DECnuziOi+KdO3LOTPT5PNr69euLtpVRZLSbGWM2m/b06le/ulgaNYqiSbsGjn798s8X3blI69atm5R9"
                "AsBURgIAwLTx6KOPjrhJ77Q4jnX88ccrCAKFYdjx/U8Fs2bNkuM6WrVqVdlN2Uw+AuCJJ54gYVOCSqWi"
                "P/3pTwrDsOvqQ0itUUXWWjnG6cpVCrpB+3lz3HHHKY5jxXFcyoifDRs2kAAAgDGQAAAwbdx+++2K47i0"
                "3lvHcXT66acX69xjpLyHPUszDQ0Nld2czfi+r56eHtVqtWK1AnRWPs++G6eI1Ov1VpE712GEyHY45JBD"
                "1NvbK0mlFNWs1+taunRpx/cLAN2u+95hAWAHLVq0SLVarbQigNVqVYcddpjiOFalUun4/rtdlmYKw1Bx"
                "EisIgrKbs5m8avkTTzxRDGdG57SfN92YAGg0GsUcdxIA2+Y4jvbee2+5rlvKiJpKpaK777674/sFgG7X"
                "fe+wADAOeZGnMAztI488UurQ4UMPPVT777d/aQmIbpcvAVitVnXfffeV3JrNpWmqOI7VaDTKbsqMZIzR"
                "xo0bJW0+r7sb5KtYhGHYdW3rBqNrnvT39+sFL3hBMV2i00mAOI61aNEihWHIiwUAbUgAAJiywjC0+VD7"
                "4eFhrV27tkgAlNHjdPDBBxf/Zw755toLu3XzKgn1ep0ArwSVSkWPPvqoJHVlDYA4jhWGYVeOTuhW+ZKo"
                "ZdRMqFQqevrpp6nHAgCj8C4GYMpqDyiXLVumdevWlRq4nXDCCcX/HcPldbQszeQ6rfoIw8PDZTdnM67r"
                "ylqrwcHBrgxAZ4L169cX53W3JWGiKFKj0WB6zzgcdthh8jyvtKKJa9as0dq1a0vZNwB0K+5QAUxZvu+b"
                "IAhMFEV2+fLlpfb+S9JBBx2kzLZGJOTD3TFSPre+G0cA5D27TAEoRxzHqtVqCoKglKJx25JlrRoWjO7Z"
                "PmEY6nnPe55mz55dSs2PJEkUhmFXrjgCAGUiAQBgSms0GrZSqRRzyjt5c26tled5chxHQRBo//33l9QK"
                "JBkmvDnjPDs/uBsDvDRNW8u8OY5cx+26HujpznWeXTO+G7UftyQBtq3iVuR5nvbZZx/FcTxixFYnOI6j"
                "ZrOplStXdmyfADAVcIcKYMqL41jLli3r+H6DIJDjtNYE7+vr05w5c2StVcVliPBY8pv/bg2e2gN+RnCU"
                "q9uTL916DHeTzLaKoS5cuLCU5ysvxrpkyZKO7xsAuhkJAABTmrVWURSVUlU+r1RujNE+++yjOXPmSJLc"
                "Svf1bgPYOQT942et1WGHHVbKiKggCOR5njZu3MhKAADQhm4qAFNekiR6/PHHO77fKIrkum4xzFVqDWMG"
                "ML11+wiFbpA/R2WOAEiSRHfffbeCICB7AwCbMAIAwJTW09Nj1q9fr3Xr1nV838YYeZ4nY4xOPfVUGWOK"
                "InfYXF7ZPY5jAihMSb7vc+xuJ9/3ZYzRSSedVMqqGvn1hhoAADASd6oApqwoiqwkPf3006XclAdBoGaz"
                "qSRJtP/++8sxDsOEtyJN0uL5odI+pjKSANtvjz320KxZs0rb/5o1a/TMM8/wggHAJiQAAExZ+drSjz/+"
                "uLIs6/j+82DWdV0deuih9P5vQ5qlSpNUlUpFs2fPLrs5wLiQ3Bs/Y4x6e3u11157dXzfWZbJGKN6va4n"
                "nnii4/sHgG7F3SqAKSsfVrpq1apShpgmSSJjjGq1mnbddVcChG2oVCoKo9Y66vvuu2/ZzQF2COf59nNd"
                "V1EUaeHChR3fdz7VqFqtkgAAgDYkAABMWX19fUZqTQHIRwOMR74u9c5utVpNvb29E/73TTeO46harUqS"
                "DjrooJJbs7l8VYfnPve5pVQtn+kym6m/v78YzbOt867TXNfVggULJInjYzvZzGrOnDnab7/9Spk24Xme"
                "4jjWk08+2fF9A0C34h0MwJQVRZGNosg+8MADpdyQG2OUZZkOPvjgHUpAzDRxHMtxHKVJqmazWXZztmjX"
                "XXdVvV4vuxkzjmOcYinNMqb0bEu1Wi0SD5UKiyhtS/truHDhwiLB1inValWu6yqOYy1evLhj+wWAbkcC"
                "AMCUZa2V7/tm+fLlpfQIxnEsz/P0nOc8R57ndXz/U017kmTu3LkltmRsec9yb28vCZ0SuBW3eN678fnv"
                "7e2V4zjKsowRANvJOK1K/IcddtizX+vQtbrZbCqOY0nSY4891pF9AsBUwDsYgCmrfW3nsooAxnGsgw46"
                "iKrg2yEfMWEco/3226/s5mymUqm06hSEoXpqPWU3Z8aJ41gvfOELVa1WuzKhVq1W5RhHNuNc3175Unz5"
                "CIBO8jyvOI6Gh4c7um8A6GYkAABMac8884xdtWqVHMcZ99z9neX7viTpgAMOoDDYdsp7dvv7+0tuyeaS"
                "JFGSJKUULEMrYNttt92K6SHbOm87XQvgwAMPlHEMq32MQx7077bbburp6SkC8vzaOZmSJCmuN0888USx"
                "bCwAzHS8iwGYsqIostVqVdZaua7b8f3nQ4HnzZvX8X1PRY7jyDGtt51ufM4qlYqCINAhhxyiJO38qhJQ"
                "V8+xdxxHaZoWvdrYuvbkTG9vr/r6+orPOzHFw1qrNE3lOI6Gh4fVaDQmfZ8AMBWQAAAwZfm+b9atW6dG"
                "o1HKnOE4juX7vvbee++uLFrWbfKgzmZWu+++e8mtGZvjONp9990Z0VGSWq2mWq3WlTUATjrppKKqPMfH"
                "trWP0Ojr69Muu+xSJE079frmyeGhoSENDQ1JEiMBAMx4JAAATGmPPvqohoaGSgkYsiyT53maP38+84K3"
                "gzFGxmkFBLvsskvJrdlcHMfKskxpmnZlD/R0F4ah+vv71d/fryiKiqrxna4e385aWwSxeQFA13VJ+I2T"
                "tXbECIBO7C//mI8CyEcA8NoBmOlIAACY0uI4VqVS6cic0rHMmTNHs2bNUma5qdyaIpDblCiZP2++dt11"
                "V3me1yquth01HCZbPgd9zpw5Xb1M4XQVx7EqbkXValXVanWz749OBEx2YiAf6p8H/Mccc4xsZuU4FALc"
                "Hvlrk5+/++67b9H7P9lTttqvG/lxsmLFiuL7jAIAMJORAAAwZUVRZNevX1/My+00z/MURdGIue3YstHB"
                "WhAEiuO4tNdvLAsWLGB+d0l835dbcXXUUUd1zQgAqXXcBkEwojhkPpIF2++kk04qeuPLqNmSj+qpVqvG"
                "931eQAAzFnesAKa0p59+urQA0nVd9fX1yRhD0bjtZBxTbPvss4+k1pDcbhiWm2WZFu6zUDazXZOQmEms"
                "tYrjuDinypaPSknTVH19fawOsZMajYayLJPv+4qiqOP7X7FiBT3/ACASAACmuHXr1pW272azqT322ENZ"
                "limO49LaMVUdcMABxfD/0b29ZfT4Wms1f8F8SeqKAHSmyddtP/roo7umCGB+bNZqNUn0/O+MIAjkeV5p"
                "02v+8Ic/yPd9QxIAwExHAgDAlLZ69WpJrd7bMgLIQw45RNVqtVjfGmMbax7/i1/8YjWbzS32/nf69cyy"
                "TMcdd1xrrfdNgR86J01TZVmmE088UY7THbcneSLixBNPlO/7RbtIEG3b6BoeL3nJS+Q4jmq1WilTAMIw"
                "lNRaPabjOweALtId77AAsAN83zfLli3rWJG4sfT19ZU+R3mq2n///ctuwgiu62r33XfvmuBzpvE8T8aY"
                "YlRNt7DW6jnPeY4q7rMrQ5AAGL8kSRSGYSnD/yUVqwBEUWQbjQYXbAAzFnc5AKa0NWvWSCpvaadddtlF"
                "ScL8/+3V3iN4wAEHyHXdrhnuHQRBkZQoM6k0U+VJtAULFmjXXXcd8b0yXov2a8phhx0mt9LqtSbZt2Pm"
                "zp1bnO9lPIdPP/V08f9uSjABQKeRAAAwZW3cuNHmN5JlzcHv7e0tph9gfGbPnq3ddtut7GYUfN/XHnvs"
                "IWstqzqUII5jZWmmSqWi/fbbT1K5Pe3WPlsM8jnPeU7xdRJDO2avvfZSX1+fpHIC8JVPrZTUGjnGlC0A"
                "Mxl3OACmrCAIVK1WSw++CQi2z+g5wb29vapUKmOu+T7Wz2/r+zu7HXDAAerv65cxRo7L22On5a9xtVrV"
                "SSedVHwtDxo7LU8A7Lnnnnre855XShumk/ZzvaenZ8LP321pTxJTBwDATMYdDoApyxgj3/cltW4oy9DT"
                "0yPP80qb1zqVOY6j448/XmEYdkURxZe97GVyKy4rOpSkUqkUiZeTTz65COrKej3yZQAXLlyo/v7+Utow"
                "naRpqiAIZIwp5uMDADqPBACAKctaq8HBQUkqpaq053k67rjjJLWGs2P8znv1eZKeDbbG06M30V70ohcp"
                "TVKFYUgNgBLkz7m1VqeeeqpqtZqstaUl1/KVIE499dQi0Yids/fee4+YWgEA6DwSAACmrCiK9NRTT0lS"
                "KWtLZ1mmWq0mY4zSpDsK2U0lcRzrpS97qYIgKCXIGz115CUveYmMYxQEQcfbgpFmzZol3/dlrS2txka+"
                "LOHJJ5/MCJ8JkE+zkVq1UwAA5SABAGDKCsNQGzZskOd5pQwTttbK8zxlWcac8R3guq523XVXHXXUUaXV"
                "cch7Iw8//PBWwJlZVSqVbf8iJlW1WtXRRx8tx3EUBMGIESK5yR6lYa3V7Nmzdfrpp5deZ2Q68H2/KP5X"
                "RkLFGKMwDHkhAcx43LECAEqTJInOO681DaDTQZbjOOrr61OWZbrkkktaQabD0P+y5c//61//emVZpiRJ"
                "SgnAfd/XGWecoWq1Sl2IaaBSqSgIAk5uADMeCQAAQGmstbrgggu2uBLAZMqLN3qepzPOOEOu4xL8d5HT"
                "TjtNUmukSBkJAMdx9IY3vEFxHDNkfRrYuHFj2U0AgK5AAgAAUBpjjObPn69jjz1WUmdHAcRxrCzLdMQR"
                "R2jhPgtlnGeDf4Z8l2/vvffWSSedpCiKSqnLMHfuXJ1xxhlyDLdK08HKlSu1ceNGTmwAMx7vagCA0uTB"
                "1ete9zpJrd7eWq0mSVtd83sitizLlKap/v3f/11p9mwRxzz4t9aO2NBZnufpne98p4Ig6Ejl+Px1zut6"
                "vOMd71CapnJch5EhE8BmVvvvv796e3tLKdqaH0cAMNORAAAAlMJxHMVJrCAIdMEFF6inp0ee57WCLmfy"
                "355c19W+++6rU089VUmSSBIBf5c599xz1d/f35Gice1L/dVqNZ1//vmqVqusADBB0izVggULNDw83JHz"
                "GwAwNq7AAKYFeuimprwy+Lx583TxxRer2WwqDMOOVOJP01T/8A//IM/z5LrupO8P49fX16e3vOUtHQkY"
                "wzAsVhR53vOep4MOPEiDg4NKU5b4nAjGGO0ydxeSawBQMhIAAIDStC/l9o//+I/q6emR1Jk5+Icccohe"
                "85rXyBhTyhxzbJ21VmEY6kMf+pB22WWXjuwzjmN5nqd//Md/lCT19/cXxyTGr31Ejeu6qngVOY5TLAcI"
                "AOg8EgAApqx8vm6+RNfoOd7ofu2v1dw5c/XOd75Tvu8rSZIJfw2NMapUKjLGqK+vT9/97nfV29urKIoY"
                "5t2FrLUKgkD9/f269NJLlaapqtWqfN+ftKkajuPohBNO0Cte8Qq5FUaF7KixXhtjTFFfAQBQHhIAAKY0"
                "bianjyRNdNlll6mvr29SEjhpmsp1XaVpqiuuuEKHH364pFaxOd/3SRp1mfae4re97W1asGCB4jhWGIaT"
                "NmUjCAJ96UtfmpTHnokopAkA3YcEAIApr6zAjREHE8taqwULFugLX/jCpCR2PM9TFEV629vepne84x2K"
                "omiz6vK8nt0lL844f/58/eAHP5DUeo0ma17+xz72MR100EGq1+uT8vgAAJSNBACAKY1epenDq3iy1uqc"
                "c87RW97ylgl//DiOdeihh+qTn/xkUfE9D/SZAtB90iSV67jFFJ+jjz5aF198saSRFfvHY2uJnTe96U16"
                "//vfrziOFfjUhAAATE8kAABMWfnNfP5x9HDTbW3oLvmc60qloquvvlp/8Rd/oSzLdqo3PsuyYv3vv/zL"
                "v9Qdd9yh2bNnSxoZRI4VUDLCo1yO68hxHVUqFVlrValU9OlPf1ovf/nLi6UiXdcdkczZ2tb+M5JG1BK4"
                "6KKL9NWvflXWWvm+L8fl9mhnjH6+81EbixYtkqQJKbo53us9130AaOEdDsCUxg3d9GKMkeM4Msbo2muv"
                "1ctf/vJiqcDxvtae50lq9e6feeaZuv7669XT06M4jsecYkCQ3908z5PjOLrpppt04YUXKsuyomDktkYE"
                "GGPkuq6yLJPnefI8T2EYSpL+4z/+Q1/+8pc78SfMaJ7naXh4WL7vF6M6AACdRwIAwJRnjCklEZAHqgSO"
                "E88Yo56eHn33u9/V2972NkljVxbfmizLtOeee+qqq67S9ddfryzLlKbpVgv+0ePf3fJk0Gc+8xn9/d//"
                "vdI03a7jIsuyImEQRVGRNLjmmmv07ne/mykgHRLHcTGiowyc1wBAAgDAFMcIgOnL8zz19fXpys9cqV/8"
                "4hd63vOeN64kwDnnnKPbb79dF198sarVqqrVqjzPU7PZVJayesRUkwfpaZqqVqvpE5/4hH7yk59o//33"
                "32aPcp4kzIs+vuIVr9CNN96o17zmNWo2m6pUKp34E2Y8z/MmZYnP7cF7BQC08I4HAOhaxhi5FVenn366"
                "7rrrLn3729/WN77xDd11110aGhpSlmVyHEee56mnp0cHH3ywTjvtNL3hDW/Q/vvvP+Kx8gAgn388egUA"
                "dJfRr43neUUtAEmq1+s67bTT9Oc//1lf+MIX9PGPf1xPP/30iAAzrxWQZZkWLFigs846Sx/84Ad1xBFH"
                "tBICmVW1WpX07PHBCJCJMdZz2D7CptMBOec7ALSQAAAATAme5+lv/uZvdO655xZDv9etW6c4jtXb26v+"
                "/n719/er2WwWQd3WEAxMbT09PQrDUEEQ6C1veYve/OY3a/ny5brtttu0fPlyDQ0NKUkSzZs3T6eddppO"
                "PPFE2czKrbRWFnDMyEGQo4uKYnqZjKVFAWAqIgEAAJgy8mBfkprNpp77nOcWqwfkw8Bd120tIbfp65h+"
                "8iDdcZyicn8cxzrwwAN14IEHbtbbG4ahHMeRnFZPsGMcGWfsHmpMT3nNFgCY6UgAAACmjPZ53NVqVY1G"
                "QzZqDeNO01TSs0PFMX3lvbn5Sg95kT9rrZIkUZIkxXSBNE3luq42bNigOXPmKEkSue6zyaH2oJBh4tMb"
                "1wUAIAEAAJgi8p7e/P/GGNVqteL77XP7x0JgN7W1v36jX0vHcYppH57nFXUC2msG9Pf3K8uyIvgf/Rgc"
                "H9NbWavFAEC3IQEAAACmFebzYywkAACAZQABAADQQY7T+dtPVncAgBYSAAAAAJh0ZfbA0/sPAC1MAQAA"
                "TAnb6r2jdw/ofmEYFsUbO4kCjwDQwggAAAAATLp89Yb8Yxn7BoCZjgQAAAAAOqaMGgASo4QAQCIBAAAA"
                "gA6iNx4AykMNAABTlrW22PLPO8kYo1mzZhX7pXcJAMZmrVUYhhP2eOO93jqOwzUaAMQIAAAAAHQQFfkB"
                "oDwkAABgAnBDCwAAgG5HAgAAJgBDSwFg+5AwBYDyUAMAAHaCMWaHg39rrbI0k+O25qZGUSRjzE6tkd3p"
                "ta7b6y9M9H5HBwmjH99aq2azqTRN5XmeqtVq0Y4syzb7eZI0QHmstUqSRJIUBMGE1gMAAGw/EgAAsIN8"
                "31elsuOXUWOMMpvJNa7SJFWlUimWxwrDUI1GY7sfZ/TH0QUSJ0MQBMX/rbXKsmxC9zc6ERLH8YjPe2o9"
                "chxHlUpFvu9raGhIjuOop6dHNrMyLgE/AABAOxIAALCDqtVqEaTuSA94s9lUtVpVHMeqVCpavny5rrrq"
                "Ki1dulR//OMftWbNmu16nDxpMFYCYDKX2xod7O/MyIWxjA74Rz/+oYceqiOOOEJnn322Tj75ZC1YsEDG"
                "GNXrdQV+IAAAAIxEAgAAdtDOjgCoVquSWmtiX3nllbr00kvluq6yLFMQBJsFwFvT3uM/1oiAydCeAMiH"
                "40/ECICxhu6P9fhLlizR73//e/3P//yPqtWqLrroIl122WXadddd5VZc5hkDAACMQgIAAHZQtVqV7/s7"
                "PP89iiINDw/r5JNP1qOPPirHcYrHiqJomwHslr7fPi9/Khrd7i3VAkiSpPh/s9nUVVddpa985Sv653/+"
                "Z7397W9Xf39/MToCAAAArAIAAKXJskxXXHGFHnzwQQrUTYC8BsHll1+us846S0899ZTiOFYURUqTtOzm"
                "AQAAlI4EAACU5PHHH9fVV18taer21ncT3/cVx7GstVq6dKmOOeYYLV++XMYYOS5vdwAAANwRAUBJbrzx"
                "Rg0NDcl1XYVhOGIePwmB8YuiSFIrmRLHsVavXq2XvvSl2rhx42Y/y3MMAABmIhIAANAh9XpdUmu+erPZ"
                "1HXXXSdjjFzXZa76OIwO3tuLH+Yf89UPli1bpvPPP1+NRkNxHBdTAXa0bgMAAMBUxh0nAHRItVpVFEXy"
                "Kp5Wr16t+++/X5VKZbOef3qnd9zo561Wq+nWW2/Ve9/7XqVpKsd1lCYpCRcAADAjcQcEAB3iOI6yLJPj"
                "Orr99ts1PDws13WVphSomwye56nRaCgIAl1zzTX62c9+1ur5d+j5BwAAMxMJAADooHypv1/96letZMCm"
                "pAAmVl4HQJLCMFSapnrf+96nZrNJ7z8AAJixuAsCgA6J41i+78txHC1atEjSs3UBxhryv6WpAUwR2DZj"
                "zIgtSRKtWLFCV155pay1ajabZTcRwE7Y1vVx9JYvEwoAMx0JAADokEqlojiOtWrVKj300ENlN2fGqVQq"
                "+s///E9t3LhRvu+X3RwAAICOIwEAAB1irZXneUrTVJ7nld2cGcd1XQ0MDOgrX/mKkiQpuzkAAAAdRwIA"
                "ADrEZq3hp41GgyHoJUiSRHEc6ytf+QrPPwAAmJFIAABAh2S2Vexv1qxZrEFfgiRJ5Lqu/vjHP+qBBx5Q"
                "HMeKokhRFClNUuYHAwCAaY8EAAB0CAFmubIsk+d5Msbo8ssvVxiGktQqzOg6JGUAAMC0RwIAADAjBEGg"
                "MAzl+74WLVqk++67T5IURVGxZCAAAMB0RgIAADAjZFmmNE2LgP9DH/oQSyoCAIAZhQQAAHRAvgKAtVbG"
                "GEVRtNla9ePdMD5pmspxnOL/t9xyixYtWiRJMsaQCAAAANMeCQAA6CCCzO7ynve8R8YYOYa3QwAAMP1x"
                "xwMAmJH6+vp077336lOf+pSSNCm7OQAAAJOOBAAAYEZqNpvyPE8f//jHtW7durKbA0x7jIACgPKRAACA"
                "Dsnn7odhKNd1y27OjJemqbIs09DQkC655BIZYxTHcbE8IICJY4xRlmXU2wCAkpEAAIAO4ua3e1QqFVlr"
                "FQSBfvjDH2rp0qWqVCrKsqzspgHTEtc+ACgfCQAAKEFejR7bw2ltRq1tB+VL/rVvaZrK931lWaaLLrpI"
                "WZopCALV6/WJajwAAEDXqJTdAACYaTrZw+wYqWLbsr1GcrqoEy7LA/pRbcokJZs+tr5pRgb/E/A3xHEs"
                "SQrDUEEQ6IEHHtDXv/F1vemNb1JPT8/O7wAAAKDLkAAAgA6x1sqYnejCHmVbjxVUPZko0gHzpTSUTNAK"
                "/t2s9dEYjSuQnj1bajalwUGp0WgL3jdrV2urOK0EhHWe/f0RHMm2JQBm90u+J20ckJY8KrlGalipiPyL"
                "BreSATYbXxZg9POVT8fIEwHWWv3zP/+zXvWqV6l3Vq/cSnfXaWA4NXbGRF6LJgPHNwBMDhIAANBhnbqx"
                "bTYi/cWJe+k/Lj9TQfq4UhNLyuRmjhzryMjT9s4Eaw8WWkPns2eD9y39Tv5nOq0fNPlHYyRlkokkk7Qe"
                "x1Yk60tZj+LQ1yc/f72+cXsi46gV7Fs7Ib3+m7VxVBD05JNP6l/+5V/06U9/euJ3BgAAUDISAABQgsnu"
                "fXNs6wIfbXhawfB9mpU+oGpt0yXftubUG7Npbv12sG3TFhzHleOZZwP8Lf1O25+YWSuTWVmbP04mmUxS"
                "JqNMNjMy8lQxgSpBTVe89zR979c3KXIl33MURYmUtooAbCvxsMX2jEq8jH4NHMeR53n62te+pve+971a"
                "uHDhju0IAACgS5EAAIASdGoUwJw+Xz3OgOaaQVXiVid65mwaSD+OOoStYf2tIfNZImV2y7UEjLPp510j"
                "Y5zW8oe2VYjA2uzZxEF7BsFRK2Pg+1I9lOdYvexE6cd3Sn7FKIqe3V+2KWlhlY7z2di6fDrA8PCw/u7v"
                "/k4//vGPJ/TxgZmOYf0AUD4SAADQIXmPs+t2YG65sUqs1NPbK9dxVUkqcqzX+pbTVGbs+ArqW0m29Tuu"
                "I7nSNnvibWpHBOn5X52HAO2lEFvBvZWiUPKkimnow+9/lX77xuv1TD2WTSSzKfB3NxUVyGSVaWILKmZZ"
                "piiK9POf/1yvftWrdcm7LlF/f7/mzJkjz/NG/Ox4R3FM9KgPgqmZpVJp3bLlK4jkx1P+Ma9lsSXGmC3+"
                "7ljH5lg1M2q1mnp6eopkmeu4clxnq7/X/nVrrTzP49gFgBKRAACADsoLAXZqJQBjJWNbc/5lHckkMtZq"
                "09T6cRld9G9bUwA228GWft46z4bxJpOMVNGg5rlP6cwTpe/cnv96JiPJUZ4AmBzWWiVJouu/f71u/NmN"
                "iqJIvu8rDMMRPzeegL596UFgMoxOUI22rQTBth7P8zztsssu2n333fWWt7xFb3zjG9XX16c0aSX5tqdo"
                "Jsc/AJSPBAAATEPGGlVkVckqcqyjzGRyTFPWSWWdVjBvpGdL9G+PMe7dt/TbYwXnmbRp3n/bQ5r8Udof"
                "KZJnm+qPH9bH3nu2fvCrn6riV5UmzdZPZcmmn5/8JEoe9Dcajc2+N94e/W0FaONFMDWz5EnD/HUf/XFb"
                "AX4+8mj0cbOl42isx1uzZo1WrFihxYsX6/Of/7y++tWv6ogjjpDv++P4SwAAZSIBAAAd1KmgzerZ8DiT"
                "ZE2mzGl9ZUvL943X1lIH2xueGyvJZiMfzTpylWiWu1FR+qROOd7RrQ80NZC2ag90cnG+0Us3bun/22O8"
                "PbDbQgIA45GmW66ZMdaxPDqoj6JIQRDIcRxlWaZHHnlEL3/5y7Vo0SIdcMAB29w/o2AAoDuMo+sHALAz"
                "oiiSJNVqtUnfV2akRFJYyWSdSDKZMiOlxshaU3TmO8p2eNM2tjF/b1PxwBGbMjlK2rYsb5yy5Bn9/z78"
                "JvUkUl/QqgOwKY0x6c9hHhTlSYDRQVKWZePa2gMggiCULT+mt5TIiuN4xGaMURRFxflQrVa1YcMGvfGN"
                "byymAQAAuh8JAADoIJt1LvDLzKZR+5uCf2taX8uMI1l3fMP/J1178uDZxESvn2qWVuioA6S0IbnGSo5R"
                "ItuBFACALXnmmWdkrdXvfvc7/eJ/f7HNn7fWjkiIAQDK0U13fwAw7RlnYivBT1fWSjZOpOZGuYOP6TP/"
                "/Ep5VnKMlXENwT9QsnxFAUn6yEc+UmJLAADjQQIAAGYAZ4qNODe2VS8wMIl6zQbNdtbo+EMkX5LrbRpu"
                "TC4FKE2WZcX0gSeeeGKz7zPlBQC6EwkAAOiQfO5sHMcjes8mb4cjPzVt8+6nAiPJVaoeM6Se5Cl97l//"
                "WpWkVTPQ6UAdhW22r20O9Y5swFTWfgyvWrVKDzzwgKy1W6wHYIyR4zjFBgAoB1dgAJjGjCRnjK5yY7v7"
                "DcAYRzKuWsUEI1XtBs22y3T2iVLalHp6grKbCEDPJsL++Mc/KkszOa5TFAtkBAAAdJ9uvv8DgK5mrZXN"
                "xndzS8/v9rFGyhxH1jiyqshVU/Pclfr4/32pZrlSs94oftZpfyvj6QVKsWrVquL/+fSA0VteAJDrIACU"
                "hwQAAJSgkzfAjjEyU7ADLjOZUkeSMrk2UjT0lPzkKb3pVbvKNMNNSwi2OLydAaWqVCpyK27npjgBAHZI"
                "pewGAMCOGj2fupt7ldrb5vt+x/Y7ODgoY+bLcSVZTZnq+ZnJJONIJm516lupp6+m4XhIF7/ueP3yNz/R"
                "gyslychxKsqyVMYYWWNlOjQMgGHNmMrGe/xu6/rabDaVZZkqlYocxxnz8SdyOsB4r/eO43T1ewQAdAop"
                "WgDokLxXrF6vdyR47JvVq6efrMs1RpqKyw+atnSFkeKoKd8Maq7zuP7+HQeqR9q0XEDaShhIMnYK/p0A"
                "AAAdQgIAwJRWZo9OlmXKbLbddQAqldagq4GBAaXp2JWyJ5LrOBoaktIsk7Kp01udbXpJjUZO6bep1axK"
                "Q379QZ18RJ/m7yK5vtQ7t1/GdTatcOCo9dbmyJpWLQEAnTfWqhf5CAB64gGgPCQAAExZU20Idn7TOzw8"
                "rCyb/MH49UZDQSBlaSYbT/ruJp6VnEybAnlHnitVlGqen6k3W6/3XHyCXCs9s/aZ4vk0enaZw6lY9wAA"
                "AGAykQAAMKUZY5SmaSk9Sv39/fI8ryh8JUlxHBfB6OhlsPKERRRFHWlfksTKBxoYp3XBd42Rq9bWrfKe"
                "fCer6Nm3qUzGVKTElZv6miVHLztmby2obhol0JYMIgkAAAAwNhIAAKasskcAPPDAA/rVr34l6dnCfkmS"
                "yHEcNRqNzX6+vb2dTFgYY6bm1d5WJFsppgRIKqoYerauuVqpN5w9Vz1GbWP9MzmSjJxN0wEAAACQ4+4I"
                "wJTVPre0DGma6swzz9RLX/pSLVmyRGmSqlqtSpKCICg9QTGaNa34OTMaGVR3mcy0wvjMOMrkFL35kmSd"
                "TKkXSZX12j1YqUvf8DJVJbluoMyxkqwcjVzixpFtewze9oCZiLoDANDCnRCAKa3sIDtNU9166606+eST"
                "9Z73vqfo+S87OZGzebBfflPGKdPoRQtbf0uqTJJRJDP8pPxklY48QHLTptxNPz7mn2rsphEBmayxso5l"
                "fgAww5T9fgEA3YAEAIApzVor13VLubEzxihJEhljFIahrrrqKj33uc/Vj370o9aa9JvaFMfxiGTAxo0b"
                "O5IcGF1mMDOaEpXxHSs5yuSYSI6JRn3PVSWTKplRxXOVxBv0j39/kaqSPEmOjFJJiVqjCKxpvc0Z25YY"
                "qEhyu/95ADCxSAAAAAkAAFNcN93QGWO0Zs0anXPOOTrvvPO0Zs0aGWPkOq7CMCyC/p6eno61qQj6R309"
                "nw7Q3UaPAmhVNDTWyFgpziIp3aA9+4e1e4/kSspkWwkAJ9NYJQAcu+khrTZ/UgBMa930fgEAZSEBAGDK"
                "6oYh9u0qlYqq1aocx9H3vvc9LVy4UF/4wheU2Uye56nZbEqSdtllF/X29k5+g0Y9Pfl0gG6e/781xkrG"
                "tpIA1kiVwFfgNeUN3603v6pPFUmpI6WVtLV+oBmZ4mgVB6zITVyZxMgwBACYMbplWhYAlI0EAABMEGOM"
                "ms2mfN9XrVZTFEV65zvfqRNOOEFLly5VrVaTJDWbTXqidpIxjqy1crK65vU8o78553DVjBS0399byc20"
                "KdBvfcNRJleOXDuyuCCA6Y1rLgC0kAAAgAmSpqmMMYqiSGEYynEcOY6je++9VyeccIIuvvhirV27Vgcf"
                "fLCSJJn8Bo263zV20/z66XAfnGWySSpjIgXeRvVUntKvrj9Hu2RSLZFmVXo0yzpyNk0bcOUqVapEqRLF"
                "ypQqlZW1O77NVHlPar7lx3mZGz272uz1MMbI8zxJKj7OdBwnADBypSQAwE7IstaQ89HBYf75N77xDd10"
                "0036+7//e/X19RVTAibTlordGzs9MsCOzWSdRFW7TnPME/rtDy7QKy78lpZvGJbvtP7ORFbGMQrcQKlS"
                "maz1hGTG2alCgPnrPRN0c+KjPfDNP59prLXKsmzE6xMEgcIwlNQqRDrTdeOxCwBlIAEAAB2SJImWL1+u"
                "d7/73apWq2U3Z0rLCxtmpjXV3zNNmfQxKR7UD774cl19zS266bZUg7G0vi7Vs1ixrSg1TqtMYGYlERTt"
                "iC0luMqWppuKRM7QBMBoURSpUqkUwf/ohN/MSV89ayYeGwAwGgkAAOiAvIfOdV25rtvxHrnpetvrWElG"
                "MlmiigakLJRrEr3rb47U2/5mFyWV3bV8tasHHl2rx1et1vIVKyVJ1qabnpMdD4O6JfCdbHnQ5OQfXWfM"
                "75fJWiubdecIhcmWP//GMc9+bj0NNSKtH5LuvOdppa4vm0ZbexgAwAxBAgAAOiC/Sc+yrGNDx0f3+Dl2"
                "avf6tQd3mVTMbTBtdQ2qTirPrFVNQ8rs00rtw9p1QVVHL6jIylFm5hWPMS1qIQBjSFVV5MxWvXKQXnTe"
                "VVofP1tzJC+H6Sgb1/VgdHKl7MTPeJM9o6dIAMBMRQIAAKYxM12K/o3Snsxo//scJXJsIk/11hdG/+3T"
                "8LkARkvVozCbL8f2yC+7MQCArkICAAAwJU3HxAYwMTI5JpKxTcm2ev3z02VTCcwpPRoIALDjSAAAwEyw"
                "aa48gOnPKJNrIzk2bFsFZLyD/gEA0xEJAACYIYyVnPauQBICwDSVyZhIJm3Kpq3QP5UjyWktmyFN+nSY"
                "OI6VJImCIFAURUqSRFEUyVor13Und+cAgC0iAQAAADCtZHKUSDZs+8om7Ym/SUwCeJ4nz/Na/694ajQa"
                "WrVqlVzXVb1eL72IIADMVKOLRAMApilrWkFAZlobgOnJUSZHYSsJULKNGzfq+u9fr6OOOkqLFi2i9x8A"
                "SsYIAACYxizBPjAjZdZKymQlpfkXTedqAERRpJtuukkf/ehHdf/99yuKIhljZIyR67odWw4VADASCQAA"
                "mKZG315npm36PxX0gWnNWsk6rhJXylJJsq0LwCSd++vXr1eapqpUKrrjjjv0zne+U/fcc49835cxRtZa"
                "WWsVRdHkNAAAsF2YAgAA01hmWqMARt/z59MBAExP1o4eATS5Wb8gCHT33Xfr/PPP12mnnaZ77rlHklSp"
                "VBSG4TZ+GwDQKYwAAIDpatTQ//ag32EEADDtGWM61tPz2c9+VldccYWyLFOapurt7VW9XlcYhgz5B4Au"
                "QgIAAKYr8+yaf+nWfxIAdsrKlSslSb7vK8uyIvBPkqSY+28tmUcAKBsJAACYxuJY8ryKTDTpy34DmMHy"
                "Zf3iOJakIthvX+6v/f8kAwCgHNQAAIDpKrPqqUn1ekOuy1IAwExj7GYzgeS0bQCAmYcRAACAUVqhQbZp"
                "yTDqBQBTjzGtXnZb0tR7evgBoDuRAACAacpxHA00M0WzjtDaMJVv6vI0LNcmMjaRwzoAwLSUqaJINTVN"
                "v1IG/wAA2jACDMCUla8rnfc0tX/eiW0i2z8Z+/dcRys3SKe/4wdaMnSKNriHaqDRq6ThySSbfsi0hggb"
                "29py7amBzIy9AShPfs6OtSWmR0POQg1oHyVWyicCOJv+NxGn785enyb7+goAGBsJAACYpsI4UWKMlg3M"
                "0mv+7mv6wMdv1XpzqBq1Q9Vw91Gqaivot1I+K9hY3haAqS6zviIzR5H6GecDABiBOz0AmIZcYxQ4Ro6s"
                "ovqwBmPp+4ukF73ll/r/7pCWO0eqYedJdlM5MOtItrJpc1rpAMv8f2Cqypfds20jADqJHn4A6E4kAABg"
                "GrKZlVupyBipGlSVZVLW42i9I33oPxbp7z5yg9abwzVg9leoBUpNdVPw3/p9eg0BAACmHxIAALATrLVy"
                "HKfrerSsa9VMY2VGSsJEjnwpkWQla6S7HpCOec3P9fWbrZ7RvmpmvcriRMoiGddVJqtUUirJWqnL/jwA"
                "47WpdgdLAALAzMZ7AADsIN/3JUlpmspxuu9yajeN+nXyef2bhvunqqipilLX07988WG95l2/0zrnYDVq"
                "B6vh7KbBZiK3wiIxwFQ3urinLKN7AGCm6747VgCYIg4//HB96Utf0oIFC7pqBIA1ktWzQX9mMkmZZLNi"
                "BEDiSFGaqSHpgUHp5Df/Sv9107DW+Mcqreyi+lBc5p8AYCL66k0e7o8M+0kCAMDMRQIAAHbQ0NCQXve6"
                "1+mhhx7Su971rrKbs7lNPf95AsAo2zTHP9uUsDCS62tDIj0VSZ/+2qN6/ft+qg3u89So7qchs4eaZrZS"
                "eSMfliUAgUmXFdvYt2rWbDoX29b1s8ZR4lTUdGuqO71qml6ZEaevo3zhD5IAADAzkQAAgB0Ux7Fq1Zpm"
                "z56tT3/607rjjjt05JFHylorz/NUrVZlrS2qcRtjZMyz0fPozyfKs+uBt13iTSaTOa3hwFnr9j9SokYa"
                "KU2kNJWGUukPK6UTX3eLrr51lpa7x2l1tqeMP0eypgg4Mm36SCIAmHCZaQX91uTbpq85I7fUaX3dmlaN"
                "jiSVmqmrQRtooztb67w9de0v7lKSXwbyFT/kS6qIW0AAmJm4+gPABHnBC16gpUuX6l//9V/V39+vRqMh"
                "ScqyTJ7nbeO3O6N9TnDeE5gLM8nU+rQqkT561b163bt/pI3u4VqX7auBdDdltkcmc3jjADqkPcnm2Gdv"
                "2uym76WbEgGxW9GQ2U1xz5Ea9J+vNfH+etUb/z996Ru/VjNR229x9gLATMc7AQDsIGOMjNPqxXeMozAM"
                "lWWZ/uEf/kFLly7VWWedVfTwB0FQQgvbBvnaLV/u278zMDTY+lpFemKNdOp539W3bs200XuB4mw3uVlF"
                "bubIzVoBCYCJVRTtVCbHtqbuuFlrOr9JJSc/rU3rtI4dadiZp8Ha8Vqevlhv+4c7dNYFN2g4lGwi2VRy"
                "K0aO40pKlG3amAQAADMTCQAAmCC+7ytNUzWbTe211166/vrr9T//8z+aM2eOhoaGym7eVrWXG6s4juLE"
                "aDiRBiT902cX65KP3KANZj8Nmz2Uyi+xpcB015r1b6xklLUl2pxnN1tRbKsa0i7aYPbXOnOEPvTZm/Ty"
                "v/kP/f5Bq6G0ooFhKQ4lx5VsZpRledBP4A8AMxkJAADYQfkc/nwkgLVWruvK9/3WsP+Kpze+8Y169NFH"
                "df755yvLMmVZqwBf+1Zauzf9k1T835WRzeymucVGco2GJN3ygPSq99ysp+whqru9Suj9ByZRJte2ev6l"
                "1jB/eVbWzWR8R1HmK6ocqLX2BP3knoU66bU36we/irUhlBq21c/vypORJ9lKcZ1pv2YBAGYmEgAAMAmM"
                "MXIrrowxmjt3rq677jr98pe/1L777jvFbsAdyfUUutLDG6RXv+smbawcqHp1N8WGkQDAZCiuDnkxT1tR"
                "I62oWZmvQbufhoLj9ejAc3Xm636m9//zL/VMIg1mUkNSKm1K7FUkVWQ3FRIorjm20tq4BQSAGYmrPwDs"
                "oPZAfnRAn6WZ4jiWJIVhqDiOdcopp+ihhx7Sm970ppJqAozNaPNkhCMrY62ktDWRWNL6UHp4vfSaD96h"
                "VTpWTTOvwy0FyvPs6hrPFtKcLMXDG0fKKrK2qqy2m55MnqM/pqfp3L+/TS9/84+0JpHqVkrb6wIYo1TO"
                "swP9TXstkIpaqwD44hYQAGamStkNAIDpyDhGrlwNDw9r1qxZMsYoDENV3Iq++tWv6uKLL9aLXvSispu5"
                "VY7NZwvbVkBipYYr/elp6fJP/FT/denx8kwoT0OSjZTnQBzb6sHcVoyUGck1rrI0k5Gr1HEUq6rI9ClR"
                "j6z8rRYvBHZUvnye1ArmXUXybFOeBuVpSK6Nxv5FK42RL5sQ1rbm6yuVrCpKjK/U9igxs9Uw/RrO5unK"
                "r/2vrv/lXXp6SMoD+J7AVxQ3lWxqnzXOpr8rD/yz1h9pp8qoIwDAZCIBAAATZKxh/XnwL41cCeDkk0/W"
                "wMCALr/8cv3P//yPGo2GHMdRmqYyxsj3fYXh/5+9O4+TpK7vP/7+fqurj9mZ2V12F5BTXDFKRPBEPGI8"
                "8EK8UCCCEvGIVzQeEdFo1HgmikaFRESjEZRDgkYSVASVnxhUFERAAUGQBZZd2GNmp++qz++P7qrt6bmv"
                "PmZeTx7F7hzdVV3X1ufz/X4/38qSbGcyHjiJByatQ2BtfyZfRtKOXdIPfyZd86KMnvaIQ1QauVZD2Zoi"
                "b3LWnB0glpybOuaInbRzVNpjjZOqTpXIqZzNqZTbTyPhIRqJ99GXvvxt/eEPd+uOOyLlC1KyO9p3s3dS"
                "bI0AqvWjzHWWgpj4aHlrOR/MSb4g7bdfQetWD+sVL3m6Hrq+qvXhJu0R36qBTE1mUmyNbJYfdz3srtI/"
                "H+l51pIwk6Q4bpzLcpLLDKpcHFIps692Bvvrkv93sz7y+R+qrMa5nlVjnH8sr2KlPVkRqZG0i5rbbEoz"
                "eKo1fz7/7QcA9DcedwD0rS1bttjGjRs1NjamOO78w+xDH/pQ3XrrrZKmCKJn4JxTrVbTNddco5NPPll3"
                "3323isWivPez+jzT1RGY7mft2zqfbc9LWiPpxxcdrz3jX2sw2KSqKyljUq4mKfaSj6dMADgfSIEpirxk"
                "AyprjUYz++o39zj905k/03W3SWNlqRF9+eYUZtHu5EWyzemfc/4IWOmCUGE+r1qlJF+v68DV0tte9WC9"
                "9Kl7asg2acjvkrddipvz7vm4OR5fSWJrkRIAzS/rkeR8RvJ7aEdxSJXsQ3XVb7fpU//xS20albaONk7z"
                "sHmuV5XMFzBhDfParuVu7dq1uvPOOzU8PMyzL4AVjZsggL7V7wkAM5PFpiATaNeuXXrzm9+sb37zm4rj"
                "WJlMZsYeAN1MAASSCpKeeoh05j88XvsM3qlatEVhLGWrvtF1P4hlbvLjkrTWx5m8xoI9NOr+TCf+7Y90"
                "62YpCqWdRanuvcz5xvbF1pwIfXzNhXGfMx4/qwI9ADDe7mA5kJM3qapYPpNVmKkprkQqSNr4IOn8zx+n"
                "/WvXKR//SZapKnKSs6TTZNwcYb9I95w0IZDRrnit7rf9VSs8Sn/zzq/q+j9ItYwUZ6RipXFOB+YkedVl"
                "U2wBCYDJkAAAgAYGVwLAPLVO4zevBEAz+K9Wq/Le66yzztI555yjNWvWdGV6wLmIJPnB1frpTdIPf7FZ"
                "u+K9pTgvP8vYwzmpXpeqblA7/IP16nf/SNfcJY1Gg9pZDBRkssoEWWWzWRUKBRVWDSiXzysThsqEoYJM"
                "Rt4Hcs7LOf4pwxyZycuUdxnF9bIqlUhxINVy0k33SEe9/ALttINVdQcosoHGS5rJrLkmlqbmFSujmrIq"
                "ag+NuIN1X/1h+uAXfq0nvfiruvZOaac5WZjXWKm5XnNp+gEAgPngqQkAFkmSEGhNDEzHB43W7TAMVSgU"
                "5JzTcccdp9tuu00vOPoFaeu29714q/Ya2TWqipP+4V/v0n2VhyiqrVEQqdlSX9dMLZGRpJLW6hNnXasb"
                "75XqkkpxUVUXqRRXVatXVC1XVC6WVC6WVCmVVa9U0yWq1dIlrkeK43j8MZjrf+aai3VpYf2dWL8zJ5NT"
                "JFNkVWXU6NGiSKqVJS+v0Vh65sn/o006VNXMOgXOGue0q8pZ3DjFF5gIGCvHqsUZWW4/jfhD9OGv3qln"
                "nXKV/vv/pF2xVKxKkqlSrCqUl7NATl6mWKa455IAa9euVRiGkqQgCDQ4OJjew4466ijdcMMNet7znqds"
                "NqsgCLq5qQCwovXiUyUA9IVxgUW88GbBbDarqB5peHhYF1xwgc4666y0cGAvTRsoSXKxsqtyqrpGq+l3"
                "f/IHucKDpCCv2DlZMH3R8chlVc+s1mh9T53/PyVtHQ0UKyMpbvzLNE0BQWBhGt33WzvxOyUBvVOkjMry"
                "uqMqvfbUizSiB6ni91As33hocgvv/h8pL8tvUKnwCG2qHKS/PvWn+uZlRd1dbnT5D3KuWcrPN1v8M0of"
                "2ZwpTipt9pDt27dLagT/URSpVCpp/fr1OuOMM/TNb35Tf/7nf67h4WFFUZQmCgAAnUcCAAB6RFSPFGQC"
                "1et1RXGk1772tfrpT3+qQw45ZMlmBJg3k2rVkrJZaWdF+uyXbtD2+oBq4VpVYy/n3LR1CCIbVC18uN7+"
                "D1dJkvJBoFAm38HSNHHbguUuCfzjtBW92au+sXgp8qZaUFfVN+rl37pZuuy6XXrAHqyarWlOs9f43YUk"
                "qMpute7VI3Vb/Ug949WX6yd/kLbXpFwuq1JZcvWcYmUUO6/ISZFiRZIi19hgnxasaD+Lu3sm12o1hWGo"
                "DRs26AMf+IBuuukmve51r9PatWtVLpc1NjZGAgAAuowEAAD0iCDT6BYbhqGiqFHx/tBDD9UvfvELnXrq"
                "qXN6ryWvIeCkMJCqFcmH0lhduuraTSq5PRT5nJQNp92Gmlbpgfp+uvYPUq4gVaLa7tZYk2TNqcvnMKQC"
                "mK3JwuRYSTIgVuQaVfbLofQPn71B2+zBqmuo8Xu+scxpfa5ROrDmBjTmHqSd7iH67d1D+suXn6k/7ZLi"
                "3CqVI6keS4VgQLWouYXNaQHlY9lsC2x00Z577qm3ve1tuvbaa/X+979fq1evliRVq1U555TL5RQEgWq1"
                "Wpe3FABWLhIAANAjWoPdXC4nM1MmyCgbZvXRj3xUP//5z/W0pz1N2WxWUqMCfjablXMTx023v9+iB9Am"
                "1cuNP6N6VnWTvnbhndpWXiMLBlQZq07bA6DiB3RvdW9tNem+kpRfNZR2eZa5xjjttiZW3/afplwaJm8X"
                "nfh7E83084Vg/d1d/27JeRFJipqXh2v2rDeL5TLS/WPSfWVpxD1YNZdv/FIzQTWTtI2+2cOg7pzqub21"
                "RYfq/+7YQ3/99v/WWPPErFVKkpMqtaqKcUU1FyVV/5Rmw9zUs2p0QvswJO8bPX2SGiZvetObdPXVV+sT"
                "n/iE9tlnH5mZgiBQEATKZrPK5XLKZDLy3pPQA4AuIgEAAD0o6ULvA58uj3vc4/S///u/Ou2007R27drd"
                "SYLmQ3WrTjxgx2r+IxI3/v6bm6Uo92BFKsjPUOPLLKufXvMHlZq/WKnXGq2kThofALYEQUAHJI3uFknZ"
                "VQVV6k5f/OrFzS75c+z6nwwtcNKuSqBdtTW6t7y/3vwP/6PiuBXubvG3NNBvWVpO/93XSWcliccwDBUE"
                "geI41tDQkF772tfqxhtv1Omnn66DDjqoUWhxmuQfAKC7SAAAQJ+oVCoaGBjQ+973Pl1yySXaZ599VK1W"
                "u9hFvlGgLFAsL6ki6epf3SOnUBmvGcukX/3zq+V9IMmpVqmkSY+lCh52jwCPmyXgJu85sLRaAzvW3/n1"
                "T2KK/JLPOFXLZcl7/eEPt89rzL+z5DLIqO7XaVe8t175xi/LcgNzH63f3MZuFcccHR3V4OCgJCmTyegF"
                "L3iBvve97+nzn/t8GvhXmtcxLfwA0LtIAABAn8jnG12QgyDQk570JP3yl7/U8ccfn05/11FJM2lTLK+q"
                "pHu31VSre5XGZn6L0dHRljeLGe+PnmGxFNesMTYginTXXa0/9I1llgIn1W1A1fBgvfYd/6sHxqRSPbOw"
                "7etSD4BSqaQ99thDZ599tr773e/qCY9/QjqdaT6fVybIqFgs0gMAAHoYCQAA6BPJQ3XS3X/16tX62te+"
                "pvPOO0/77bffuN9JWuqWdoMabZixMoqU1ZikH/z4p/I+p4GhoDG4ehr33hM3WvyDif8UmVmzXdilS7se"
                "aT/GMuFt95IKG0NUikVpLmeZmRR5STmvKJbK0Xpd8P3NuvYuKTuUU10ts3q090Awayxd5pxTEOweyzMw"
                "MKB/+qd/0h/+8AeddNJJkhqFS1t77fjAq1AopMMAWpckudeVhCUAIMUzEwD0KYsbxQJf9rKX6dZbb9Ux"
                "xxyT/qxjVbZ93JyiLJbktGOX5ILMrGYjG1glxXGkIMhIPqAHAHqG81KukFUwUzGLqV7vGr0IqjWvYjys"
                "kttHnzn7FkWZnHaOVVUpVdTBGS/nxTmnOI7lvdcpp5yiG264Qaeddpqy2SzXKAD0MRIAANCnfOAV1SPF"
                "cax8Pq/vfOc7Ouecc7T//vsrjjtYLdxXFfuqfMZr2/ZGD4W4Hs3YTXnffYYlJS2NC+sSDcyL04ThLM25"
                "AOUDr7gZ6A4Nzf2tA3mVKgU9UD9AH/v3n6oiqVKvyMVOgWUarf6Trb9H5PN5HXTQQTr//PP17//+79p3"
                "330V1aN05hEAQH8iAQAAfaperyvIBOm0Ws45veIVr9DVV1+t5zznOZ3ZCC8paPzpMk4juyT5jOIZuv9L"
                "0v4H7CvvnaKoqqhWmfkFwGKaIYatVCqyWk3ygfbYo+Vls2r89qrVYmUH9tZOHahvXymVmz+pWqywDxJe"
                "73//+3XNNdfoRS96kbxrPC46T+APAP2OBAAA9KlMJqNqtaqoHsk5p2q1Kknaa8+9dMEFF+hlL3tZR7vV"
                "R+ZUjhvF/WZsIHSx9tlnL0W1mvK5sNGi2ByA7VxjsXRxzcXGLXHbf7ury89W21RrE76/1Fh/J9ffXjOi"
                "dcy/b7s8vEn5bCg5yftADz/4wAnvNZNqTdpZyejCy27XLjVmyYglhZLieJKEl3Pjlxm0j7Gfy9L6Hsn0"
                "fsl4/xe/+MX67W9/q1NPPVVr1qxpTDParNPRPt3oXLap9V7EEAIA6B4SAADQp8bGxpTJZBRkGnNyZ7NZ"
                "bdq0Sae+51Q97GEP04UXXqggCNIH/CVhahT7iyVFpoGs5H1GboZ/XZzqetITHqZ8KJXHyi0BgbXOnQYs"
                "rSni7NhJlVpNgwWvuF7Vu97yCgXWSLDNYoZLxfLKD6+Rsnvo0h/9TkULFGl3rb84tq52o3fOKQxDZTIZ"
                "1et1SdIBBxygyy67TN+68Fs6+OCDu7ZtAICl1ft90AAAk/Ley3uvcrmsO+64Q//8z/+sr371q5KUBtSZ"
                "TEa1Wk3ZbDZ90F80TpJJPs5K8oplWjVUV8ZLXl6yeMo6ABnt0rpV92l1VirH0lgUKFKzbkCzRdacU2ue"
                "mkZDLLrJzilnkpMiOTnFevyDpaH4FoXaJW+Ss7iRp9LU0/GZMoo0qEgD2rRJygYZlaIoPZvT/g1dTAIE"
                "QaByuax9991Xf/d3f6e3vvWtjdZ+7zVWHFvaxCEAoGvoAQAAfSqXzemaa67RK1/5Sh122GH6j//4D5nZ"
                "uCJdlUpFZrb4wX/CGpP0BfJSHGson8Q003fhzmhMG7L36MSjMwolDQ80CgIq4h8mdEdrLN5o5Te5uvTB"
                "v3uqCpU/KKOxxg9nkYiKlVHVVuk3N21SZGqZMrMzgytmI4oinXbaabrxxhv1jne8Q1LjfiFJw8PD3dw0"
                "AMASogcAAPQoM1MUNar853I5xXGsWq2marWqK664Qp/5zGf085//XJJUrVbToD+pBdD6PkmRwPbvL0js"
                "JfPyiuVUV1aRHvPIfeSaXaXl3JQNnHmVtbZ6u972V0/Red/+se4pbk9/tirMqRaZalGsuOX1yfYn293+"
                "9cLNFJotNDUx0/uz/qVd//Tr8pJy+UBjpUgDWSmOpMMfIj1i75IGbZNCKyt2UtA8J6eb5cKUUVXDuuHW"
                "22Rxs1NBc/NdnEwtOLdUwEJHxSTXSRAEOvroo/WpT31KGzdulPdeu3btUiFfUOADRfVGBc+ZCv4xEwAA"
                "9CcaWgCgRznnlMlklMvlJEkPPPCA/u3f/k2PfvSj9eIXv1hXX311owhgFKVFtjrGmksziPGqazhrOuLw"
                "jZKr766yNoXAKvLFBxSU/qBPf+RZGmh+30saqVTofowlNvHxpxZLxVKkVQWnUkVaG0qn/+NztCG3Q2uy"
                "ZXk1ElvNWQKnFSujmgZ1w83bVJVUr9Wal0zywqQUYecMDAzo0EMP1ec//3ldcMEFOvDAA1UsFlUsFtN7"
                "DABg+aMHAAD0KOecyuWyrr/+ep1//vn60pe+pNHR0fTnSXfdOI4VBEEXqmvH8pJiBQokBbH0pMfvK+fu"
                "aDSTTjcVoDPl8tIqu19PeeROnXSMdN5lUkWB4lqssXJRsfNyrrUGQK90nkZ/a5y1u/9sdP8PvRRkpErV"
                "NBhIl17wV1pdvl7Z+g4pLsn5Rk2LyEkubvR8mUqsUOUop033NWsFmBp/cZLJzzQD4ZJ41KMepa9//eva"
                "uHGj4ijWrrFdGhgYUBiGkpS2/AMAljd6AABAj/rOd76jpz71qTryyCN1+umna3R0VPl8XrlcTt77dNqu"
                "bDarOI67MrVWY0xzIxEwlJXWDo5IvqzI+RlbSZ2XslbWqsrNeu9rHquTX7Baw4oURCZvsQJXVyOL0Fxc"
                "PG3QBUwnnvC35rj8ZuHJQk7KVKU9s9L3v3GyBsu3aI/sdmVdSYrj3UUorXFux9MNAXBe5bopzDVyYSZN"
                "OeNAp/zqV7/SE5/4RB133HH64eU/1OrVqxWGYTq0KCbBBgArAj0AAKAD2oPzKGq0tnnnVavXFASBwjDU"
                "Pffco6997Ws699xzdeONN054n3K5PGHse61Wm3SdnRqj63ykSiy97BjJ1+6QNKYZxzdbRooC5cw0UCur"
                "4O7Se4/7M/310Xvqw1+4RD++VhozKYob+6kwmJdqkmJTIN+oj2DNfeCbwx+WPAHS7QCJ9UuaUDl/Tud5"
                "6ynipDhu/CkvFZz0/GdJ//jGv9RQ/HOFdr8KUVlSVXEyft9a3qOZBJh8pEssF9SkQPKhpHpjHTKTcyZv"
                "UtS2P5d65st6va5t27bpoosu0kUXXaSHPvShevvb365jjjlGGzZsUC6XG1c/JOMbMwLUajV55+UCxvwD"
                "wHJAAgAAOsA5Ny5QSRIAzjtls1mVy2WdccYZ+vjHP66dO3em3ftn877d4L2XvFNcjxQ405qMdMrxf6lc"
                "dKNC1WTeycVOmqZV0cwpMCdZRXnt0Hq7U0NrTP/6Dy/Vn3bm9JXz/1eX/WSnimWptqusUI3YKwmckndO"
                "4zG3e8Hy1MjxWJrrSb6ea2oiI2ntKmnXmHTggdLTnrSnTj72SVqtTVpV+q2GwlEF3hot/3E05/PKqaKc"
                "36VH/fmAfnVbMe0t0Mg11Ju9Abp7ov7pT3/S2972Nr3vfe/T4x//eP393/+9nvzkJysIAjnnVKvVlAky"
                "aS8BAMDyQAIAABZotkF4VI8UxZECH6Tjbh944AH9y7/8i774xS9qx44d6e9673v6oTuOY3knZXNStRLp"
                "UY/Kaa2vaQ9X066xmpwPZBZPE+JEbTGQU8YVZcVbtWdmswZCr0++eoP+5Q37K47r2jkWKjN0qGoa1u6e"
                "2M2m2+b2mJmsh/cZFs75xvFOrrn2P2crpxEFY7doKFdR3dVULu1UwX6pICpq7epAigtSrSLFjWSDG9fS"
                "3zzHpmmxz6iqAW3RM5/0UH310usVx42ZAJ1aEwlJYYDuyOVyqlQq2r59u37wgx/oBz/4gdavX6/jjjtO"
                "p5xyig4/7HD5wCuqR/IBI0YBYLkgAQAAHVKP6mk321t/f6vOOOMMnXvuudq+vTEFXhiGaXf+boznn6vA"
                "O6luGnTSZz/yZhXiH0mlMRUyThZFik0Kpg1womb8E0gWSSopzAcKKzuUDxrd+l290c16KD+gYqmmUjQs"
                "BabY7Q76vA/GvaunC8Dy1VKnLl7ANZLTiFa5TcrWxiQv+XxjXH89qqpWDBT6xuORWTyvHiWBqipopx77"
                "8D9TVtc3kgfWW4WXyuWyvPcaGBhQsVhUGIa6//77deaZZ+rMM8/U4Ycfrg9/+MM68sgjtX79+nndk/rh"
                "PgYAKw0JAACYp1qtJosbT/VBJlCtVktb9uM4lnNOlUpFzjkFPlAul9Oll16qM844Q1dddZXiOFa93kgK"
                "1Ot11ev1aVsye23e7TAsyJWKeulfSuuD6+Vq2xRZoIyZLIrkJ0Q7SaAejfvafJR2kfYWyYVOTpaOt/ZO"
                "ClXUGt2jYfeAai5W7OLd+6M9xiDmwDTMSU51+aDaOBPNK6pLgfMKgqykWJEieUWSl9xM1SwnEbhYAypp"
                "1457tD4vPVBsnpbNczoyNcerzP4922sNTFeEcDrJdVOv19OvvffpdKKJ3//+93rhC1+ovfbaS0cddZTe"
                "/OY36wlPeIK8b9TgiONYlUpFhUJBUT1SkNmdiJss8E+GQbUPhwIAdBYJAABYJJlMJq2oHUWRCoWCcrmc"
                "du3apUsvvVSf/OQndd1118nMNDQ0pEqlonq93tNd/afiJbm4rJxJ733jk5Sv3iQX75JzjakIG63wU0fi"
                "jZgqkhQoVtDsDd1MDDgbN8DfxVJgktMuBRqTU6xkRvXJC7ABk4vd7rOyMXdFkqVq/TNuBP+S5ttN31kk"
                "H0Ua8FW96eQj9M5P/Vyxb5zxjRxAoPaiiuaWvhDgXCQFAe+77z5ddNFFOvfcc/XgBz9Yf/3Xf62//du/"
                "1eDgoAqFgqrVauOaD/yEwL41EUDQDwC9gQQAACySUqmUTs+Xy+W0c+dOffGLX9R//Md/6Pe//70kKZ/P"
                "S5JGR0f7unusk1Qrx3rvGw/W+uwDWhXfK5lk3it2Jue8nE0+r/j4KdQi+ThsBj7JvOz1thc0kgDmvKJg"
                "9z7z1lsBE3pfYEqnp3QulrlYsUuC/0zjnJIkC5oJqfkHrS7IKCpt19Of9DDtOSBtLTda/mPnZc52F6+0"
                "ZMrMWOZMQfPimG8L/1yZ2aT3IjOT942gPgnyN23apA9/+MP6+Mc/rmOPPVannHKKnvGMZyiqR4qjeFwv"
                "AABAb+ql4WgA0Ndy2Zzy+byuvfZavetd79KDHvQg/dM//ZNuvvlm5fN55fN5xXE8biq//tFoLfWSQkl5"
                "SUccLL3oL/ZVtnKvwsgUmMlp8qA/Mb43dVvQ0TbFmlzzBZYERI2ATc1p1JaEzXPpFWz/jJKkUZJA8oql"
                "ZHHx4uwPC6TYKfQlrc7crbe+dkOjzd811pQmIUySebnYj8s19ELvlt01NhpJzSAItGrVqkaX/yjSN7/5"
                "TT3zmc/UU57yFJ1z7jmKLe7rpCYArBT0AADQt5KWq6keOqfrjroYyuWygkyQdvu/7LLLdPbZZ+s73/mO"
                "pOZUec3tSFrQkq9n0+1/qZMEs39/L1kS/Dc6Th+wSvrmx56qNfqd8laU4sZYfW/JWOe42Um/paOzq+8O"
                "rtJDYZLVmx2td+8Ta/25JLlmoJZUY0+G/y/yLprv2y32dswX2z83vjnapNFu3Tg/20+9qczm+hnMmlzt"
                "dr3wLx+uz/7nVu3cIblM3LienDVTaq4xNMEFkovlFDe2yyWzDzTbatpWN+99Nc19sPVnZpZOB5honakk"
                "Gcv/s5/9TD/72c/0+te/Xi996Uv1N3/zNzriiCNUKBRkZqrVaqpUKhoeHpaZKYqidBpUAEDn0QMAAOZp"
                "33331ejoqC6++GI97nGP0zHHHKP//u//lvdeYRj2YSv/5MzF8qqrEMYKJO2fl/77qy/UGvuDVsX3KbBm"
                "l/3G0Hy5OXfNb7S+Jo390720tVU0dou7ND7r/Jal2B62f2m3v/WcSpZF46JGMO/KyrmdGvJb9K8feo6G"
                "JGXq45Nd49ftFctP2MZumSlZ0J6E/a//+i8985nP1IMf/GC95z3v0S233CLvvfL5fDrTgCQVCoWObD8A"
                "YCISAAAwT3fddZee9KQn6bjjjtMNN9ygQqGQtu5HUdT/3WGdyVqio0wcab+8dMVFz9Ve2euU0/a5vZ/5"
                "ccuiB11Ar3DW6PHi6vIyDUY79Pi9tuuDf/0grZKUDwLJvGJlmi39XrKMJK/Ye0XOp4mNpTZTT6rZiqJI"
                "QdDoEbVlyxZ98pOf1OGHH67nP//5Ov/88yVJQRAon8+nMxAAADqvB/LLADA/9913n23cuFFjY2NTTjvV"
                "aikC8kKhoFKppCAI0qmxEr5tHrx+SAi0DlOQs0aW2El5kw4oSBd88XnaM3u9Bt3dKrS39Kfj9xufO22Z"
                "nWJdfsqfzM5it5AuNBnR7RZbtr+z65u2h49rjiVo/kqkrMbKazRiB+mkd/9cv71X2uWlmvJyiuWcV5Te"
                "Hxo9YpyzZo2Cyc336mm/Dy3mfWlgYECVSiWtGZBMhZrL5XTAAQdodHRU99xzT1fuhWvXrtWdd96p4eFh"
                "nn0BrGjUAACAeXLOpQX94nhiAax+CPgTk267SflQimvSgcPS987+Sw3b7xW4XQoUSFMW/EtCE9/y/+5b"
                "rHnUu7V+tn9hOtrbJHZKCwo4KVBNGW3XuoFhXXjGM/TiU67Qz3dI+YGCStWKJMlFtZYrJpkRI5Y1ryfn"
                "ez9uLRaLkhq9AVoTJKVSSTfffHNf3RMBYLnqlecyAEAPCZy0tuCVrUlHPkz61tnP0LBu1YDuUWjlbm8e"
                "0NuS+QSTGNhMAzlTwT2gwdqtuvirz9KTHyLVituleiNotuZ/jcRaNO7l/ai9RgDBPwD0BhIAALBMtRZI"
                "m4tsNqvBghRXYn3w7x+rr3zqydpD1yvw2xT7umLXMn7XTbKk4hmW/jZVUbl+wfYvLQuaS7NBvzZal6pj"
                "KmR2aCi+Rd/8wrP0wiMaMxAEjYn/mnU0Y5nqzWUe14mLxy8AALRgCAAArBCBc4rMxs1BnnSLdmqE5AVJ"
                "g5mqBrPSv3zkOTr0oFjD9evla/crzEsyyctRvA+YhqklxeWkwKRwOFR9Z1WZwaosHpMqu/Sxdzxej/z+"
                "Vn32K3eoLKneHDmQGJfYsMa0e41pMOO2GhoLragBAFgpSAAAwCLpnWn/2ooPuljOpECmupnCVTnVKhWF"
                "LitVa6rLtEdBCkrSQXtLp7xiPz3jiH20KrhTA/EO5d0u+bxrdOF1kmTJH+Om7Es+floL0JL1j/9693a1"
                "d0JbWAiz1EXkZnr/ha6f7V/Y+/dSUsqZk493b5DJyUU1ZQYlMykXSGv8qFbpD3rL84f1yqP/Uie/58f6"
                "zZ1SxaR6XQq8l0WRXOBlUSx5l14zGYt3jy6QJMWSIwkAAJgZCQAAWK6sGWA7SYpVaQYktVJFCp1Urqrg"
                "pIFAWhtIn/rUMTp4n5pWBbdpdfY25ayowKqy5swGcQ8FWECvc83MV5IAS4fjOEkuVlaxstquVdqurMb0"
                "1U89W7++ra73/dMVume7lM9E2hlJcdQM6+NGkK/mkIfW9FksKXbx7mk2AQCYAgkAAFh2Ykm+MRNZGnx4"
                "eRcolwtVqoxJ5cYUf4c/TPq7Vz9Rhz80r0L1ZmW1TaFGFcaRnDOZxYqnKN7V2mLr23oDSJpFBbP+aq/s"
                "xXHmc8H2d0faE6b5devnaFypUt52aUPlOj193z30ky89WbfcVdEXvn6NrrxOuj9W41oySRYrtlgWSNEU"
                "+6OxviQJ0F/XGABg6ZEAAIBlyqvRam9Ocoo04CNFpaqGJT32UOl9b3+lNu5pylRu0NrM3fK1LSpkTfVq"
                "VUGsZkGy2Yldb3XBBvpFLClQWUNRWUFmTJXofgUbBvTpU49QOdhXZ533M134P5s1Uo61y+LGdRlLzic9"
                "fJpBvvm24B8AgIn6NJ8OANJ9991nGzdu1NjY2KRTTLWPyV/saah6Z8z/RM5MTl6N0D9SKGlI0gueKL3n"
                "HS/UcHa7MrXtytlOZbRLoZUVmBRYLKneCCqaEf1sW17bEwATXjbD7t9dE2B2rZbt27XUY9Bn0u0ECNs/"
                "/c8n1qBY2Prmf/0HMtfstu8jmTP5WMrUJZlXNeMVKStfDxVbXnU3oFG/l376h1j/cPovdOcDUuSzUlST"
                "yRT4rOI4anwmn2zT1NdQ+31wpUzPt3btWt15550aHh7u3Rs3AHQAPQAAYBlyzbr+hVCq1qQXPjmrT77z"
                "RA1n7lUY/UGZ6H5l4lEFqkoukuTkLdtoRVRGsrrkTMY0YsASahTWdGn1/0Z1f6968wFtpySpYA/oyQ99"
                "iL5z1st146ZA7/qH87R9RAqy0li1qkCSk1dkrlELoPW6pSYAAKAFCQAAWIZi12jxXJeXvvfVY7TPwD3K"
                "B1erumuLwqCsWmVMPhc2Anynxi9b0pW4M0F/OjuANPuxBkC/MklOMhcpdrt7PATR+N4LSe0O88m14RVY"
                "Vevi2zUc3K+1D8rr/85/pu6v76nTPvxNXXu9lAmlrbvixvSDLm4M+7HGa9O/t27KJN8DAKwMJAAAYJkq"
                "FHJ6/OGr9KD8vRqu3ihlYsmqCiIpzCWByO4oIHZxc/RwIwGQ9JP1tvgF2Mw1q5W7uDmgeffP5tS1f9at"
                "m4uU1Jh3a+piJVWmWX9zfvjF1eH9u4Rag96Fdv+f24rHf7k7+Dd5k7y55nY1eu0k19vu68DLWU3ZqKyg"
                "NKLAS7XivSrU9tY/n/ZMVaMNOv9bP9HXL7xXpThW3aSaGktyVMxJPjI57xR14jMDAHoWCQAAy8ZMY3KX"
                "uiZArymVKhrdFUmurjguS3WnTMbJWaNkv2sLFr2z5nCABmsJ6uYzPnzaWQHMS5ZtBv/l9NuxWoIza01H"
                "TLWC3QHqgkPQWX3G3evzbg7JgEkC8ziezxZPvX4/xXo0RcjXPrtDPGmwP/VnHLf+eSQeJnz+OZ5j3rdt"
                "22yC+mQdi5AAmHpzo92t6zZ+pa2JB9/8otFSr8YUfzI5mYL0zRsBu3mnIOvknSnjpFAV7RduVU2jqmey"
                "ettfrdbrXn6g7tnqdPq//p/+7/fSNkkWBrI4ak7l6RpVQb01JhVY3rc/AMAUSAAAwHJmXtOFxuMD+860"
                "4jbmMI8nHWrQOnPB+O8u1PT7YfbvMU9Jb4elXv+irGcO61uS9S6dTrX8T+hiP0WvlkkTa22v251oidK3"
                "ylhdoY0q50YUZ6SaC7UqHNaavdfrjH96skb1YP37d2/Uly+6TrsqjRcl2+ObXQsixt0AwIpEAgAAlinX"
                "EnU41zvD7H2z2JlrtvyntQCaGxgkY6WbAfuihpXzDVInS6TMK5hsaY2fyyDsOa+/vdV/FuuaUDhuhn01"
                "6frn0MF8wYPQe+WMbhdIagyx0biu/I0Tu3H+N36nsQvm2Cm/Ma+nzDXeQ1GkwNWVzZa1q/wnhf5+BcFO"
                "/fVLDtSjH3eQXv93F6scp2tXIClu9vfo/ZQNAGCxkQAAgGXLy8z17lCHlgCy0cjppMjSuC6pjO5drIX3"
                "AkgKHC7w9S3bMbf4dWKQN7dhFbNdf9t6ptnI6dc/cX3txr/13EeWL3Tawd6dyy1Kk1qNsfyNLyw2eZni"
                "uBF6B85rPvutnbdAFseySlGDYUY+GFNcu1uDLqshG5aLpWwmUFSP1Rjo4dXog0M1AABYiUgAAMAy5ZxT"
                "HMcys0Yw3QxEXDMK7nxaoDWYjHePjE5aRF0scyaXDaV6XXFscibFkeR9rHlPuy4tXrQ4btjCHPbgJIH4"
                "vDZppvVPKPc+zSbNeX0Tfjj1emdh4YekS4mt9hOx9esobpS1yARSNqNorCLvQwU+UGyxzMXNmTdiRc19"
                "622Ou881u8gokhRI5pUx35i503mpHivnQhUUKmeZRl8Dn1E9qDSLbKiZBDDRBwAAVh4SAACwjJnZhGJv"
                "vcE3Zh1IqrLXG62m9SCjUiWUC/dSHAypVg8k1RU4P2ORx9mZb8DTTF609lqYz/a0dLOfW8+MOa5/wlCH"
                "iZ/bWgPoCbMbTFzfhFVMtv45DLFYaM+UxTkf5sbiRg+VZNutJUHinFekWJlMVmE2oyguqu7GVLC6fL2k"
                "jKtJzhR5J5lTpjkLwJSm/XjJCxvDDGS+mYdo77nR/mfyO7G6lkABAHQVCQAAWKacaxnlO0Ww1Drl3kK7"
                "ZM9sd7AUOynyjUrkmaixeZGTinFOpfyB2lrfR7tqf6avfuMy3XjjLbp3k1SuLPX2zc2cw8+2Fyw0LzPl"
                "+me5YYu+/jnukAWvvwtjAJJ1TvZntSZVJe27l3ToIYM69iVP1aEPHlR21x80bFs1GOyUU705+t6rMVFf"
                "+24LJFcf//Vk2yG19OOpKwp2/yRWqKqTyj5WJVPfnRIwL1Oc9r2J21dOPgAAVgQSAACArjPLa8yt0/22"
                "Xjf+0evUj/1Qt239oVwQKI6cIlkjbHJz/GdrMSvTt7WSuzlNAzhxvPW8WsBbtmHK9U+yrknfaqb1T+gV"
                "0Laa9vXPcr2zXv8MutEDoJXZ7noVcRyngfa2+6Tf3rdLP/z1pcrF0qtfMKBXvuAIRe4B5fSAnHYo8JXd"
                "CZB0GsDknZsl+5vF/qbUUmcgEcsaQb6LZc43r5qWl1jL7xPwA8CKRAIAAJZIEuAEwfhWvCiKFIah6vX6"
                "ZC9bMrsDNmv7syGeIZ5a1B4CUSNeDIKsJK9adl9t84/RK//2Qv3mLjXnPpcii9IZ/GJJsU23z5LP11rN"
                "fi4bNVNAP37dbi5N3pNsh804J91kyYuWLudTrT9d1/SfZ3z8Pf26JjNh/XM8P5ZFAmAaW0cb7ff/el5R"
                "X/rmj3Tel1+l/dZs1WD95xoMxhQ1m/EzkST5lmA/aO7LqC0x0LLuKdbpm68LJLk4Ixdn06k1vUmxnGQ2"
                "+XSIM+1OEgYAsCwsxuTKAIBJOOcUBIG892mw4H1jLHung/+JGzdzwL+UGvvEyeXWajTaU5vLB+iYky/U"
                "r+6SsgMDCgpD48PPhRYA7MRndTb9MqOka/g817cgPA4sKieZAtUVaEwZ7ZD0ktf+pzaN7atybn+V4pwk"
                "KYglxX53wN+cOlDykk3e/X8qPm4E+d5M3mJ58/LNXhzefEuPjmDO7w0AWD74Fx8AloBzLq3CnwT7hx12"
                "mM477zwdffTRPTM1n7ndS2fFimPTttFYW9yj9Mq//5Hu2illc1nVolil0ui43+5yYy8wN6bmkIhIsowi"
                "5WW5rJ79qrN1x8iDtK26n1xtjVzNS3FGkpe8yebSzaY5dMDHjWVyvpFPmGw4h2tbAAArAgkAAFgCZtac"
                "fs/pJS9+ia644gr97Gc/09FHH60/+7M/U6FQ6PYmdlUsryCfVWboQfrFrRX95m4pGgg0VqmrWCmrkM11"
                "exOBBXG2O66O5bW9HCuS9Fd/8z2VMn+mmlvVGIcRN8v5xY2/mtXVmNNvbjUVpt0WEeMDABpIAADAPDnn"
                "0kA/WVatWqVMJqODDjpI73znO3XzzTfrggsu0F/8xV8om83Ke68oilStVru9+ZIWsQf5HJnLKHJD2l4b"
                "0GmfvExjgTRWi6QwlvdetXpNzildJGkuNffGr0x9Mn45mZ4N/SDp5ZMsuzVPVHPysZNUk6kieae6k7aW"
                "pVM/8r+qZnKyjElBJMXNIUHWHBHgm9P0Way4uSw6a1sW6IMf/KBe8IIXaGhoSLlcI4GXzWbH1UBJ9lO3"
                "6zcAwEpGEUAAfavb3ejjOFYQBAqCIA3o99prL733ve/Vscceq9WrV0uSyuWyAguUyTRuufV6XVEUdfch"
                "2Jq19bq0CZEyKmm1HtiV1VhNCnIZ1Wv13VXVu7NZwCLx8ubkFMsrahT887Ekp1rd9IvrpV1+Dw3mtiis"
                "11TdVVEmMz4eX4wHNIs7d49829vepkKhoHvuuUfnnXeevvWtb+k3v/mNgiBQFEUKgkC5XE7FYjFNhAIA"
                "Oo8eAAD6Whx3N1RMWv6PPPJInX/++brhhht0yimnaGBgQNVqVXEcK5/Pj2sFSwoDrmR15bXL9tA5F10p"
                "q0txsa5MPSMf5dUIfdqn3Gv+6XcvQG+K1d6bo9HDptnVJpDKkv71q9doW3SgqiooyO7uhRO7Zh5skWJ3"
                "p6VJBLT3gLjpppvkvddBBx2kd//9u/X//t//009/+lO99rWv1f777y9JKhaLadIUANAdPEIB6Fvd7gEg"
                "SS94wQv04x//WD/+8Y/1whe+UJJUqVQUhqHMrNGdvVYb19qfzASwkplCRX5Yv7hWqjan+Esqlpsmzl8O"
                "9L2WrvbmpO9fKY3qQYqCAfmMJDl5c4s63WYn75HZbFZhGKparSrIBBoYGNATn/hEffazn9WvfvUrXXnl"
                "lXrEIx7RU0OgAGAlYggAgL7XOha/kwqFgr70pS9pzz33VKlUUj6fT39mZgrDMB0mkHxPkvL5/KL0XJjp"
                "85ri3fvFTNZskXTJ69pyEIsZeMyGU6h7N0s1SZGczMcyFzcqlruJ+yfJmaSbnwy1Tn91oft0bq+fsP9n"
                "3H/tv9D+dZL0mN12TBwW3v5+S9vFutsJuG6vvz2JNyGpZ40jEjcvNGcmaxYGNEkjVSkO91Op+jvlfeO8"
                "diYFsZvyGm01XaO+KZbzjRd7Nc4oa/6n5v8nedGsTPW577jjDh122GHp11G9cf5557XH2j105JFH6vGP"
                "f7xuueWWdCjAQsw1iUriFQAaaGIB0Le63f1/LtqDlW4HL93mzMu1FCBwQdAI/hU3C6ABy0Pa8G9Orjnn"
                "ZmzSaEm67oa7Vas7KdN4HHOxl4/GXxsLWvcKv88AACYiAQCgryUPuN1u2Znr+ru9vT3LTRw/DfS79ng+"
                "llSNpHs375T5QHHU7PliPpkGoLEsAqelSQRMNguC7+HiHNxzAaChd+/UADBLtHL1p6QHR3L0zKzRrT2d"
                "VnF3d3+gX03VmB9IWjUwKJlXubxE616K6QNnoVfvyb26XQDQSdQAANC3Wsd0duPBLp/Pa3BwUJImmQt8"
                "ojiK5Z3X0NBQWreg2zo97r9VvV5XLidZTbKovnu8c/tQ6mQ4tBv/p8Vu3Ndz1Qv7fzx6PSwn0/Xi95IC"
                "Lz30ofsqcLfvPoddPOV1MOE9pjl9Z31JLOASaL9+stlso+5As/REUoOg9fdbl27ovWseADqPHgAA+lY3"
                "g38snHNOg6taStWlk6A3ixbGkxW6A/qflzQQSuvXOGW8UyHrJBcrDmLFXoqDeNJCmPMVu86ml3r1ntyr"
                "2wUAnUQCAEDf64Wxnd7P7XbaC9vcbc55HXb4aoWSgjDX7c0BOsY5qZCTQrdNq3IZ1Wqm2Jkib6pkYtV8"
                "Y6pAW9BtojGrRtz8uxQ3c2xLV2Ojl+9rs+mlBQArAQkAAH2rV1pzemU7+ol3FWVtm/7ySQdrIC8VBtoS"
                "ADynYxlK7hWBpNf91QYNxJsUl3cqCBojMmMnmWskAxZpIgA0cZ8GgAYSAAD6VhzHXZ0FYNWqVePW2wtj"
                "XPtFqF1aHdyuJz2qIKtLissK1AiMJElOcr55XJOmUPPjF6AXOZOcyZztPnWd5Jsnt5lpKCOd8OyHaQ93"
                "h4J4VN55Odc4/7MmhZr9GH83ybKU2u9v7fe9RjHP3rz/0QMAAEgAAOhjvRJk98p29BOnqrLaruFwpx5+"
                "kFQeq6Y/8+nE6UD/cubk0vPYlM1mlA2kYSe95Bl5Ddlm5W2HvKul1fqd0vzBojLHJcV9GgAaSAAA6Hu9"
                "0KrTy/Nf9yoXOJVLO/XKlx2uTNwIUiI1gp8gljx9oNGPmk3+3ry8eQVmCiRlMlLOSY8+QDr1NY9V1rY3"
                "f333mHy/iEPzYx8rdnGjjoCLJbd79P9Kra3ZC/9WAEC38cQKAOiKuGZaN+h01OP30kPXNeeldY1/mPjH"
                "Cf2tcRY7SYE5BbE0NlJTUJe++C9P0bC7XRlXHP+KeTRQzzmcJf4FgBWPZywAQMd5k0KT/K57tMF+pe+c"
                "/TQNOCnjpWwo7Z5C3CezAsrMaXd6gH++0FvG1wOJFKkmkynvCvKShgPpy597jvJ2rzLxFnkry0xSPJua"
                "IRPb7NO12cSlG1eH917OOVUqFQWZIK26P9UCAOgOnqAA9C0eIvtb4KTQqlpl92u13a7//soLtc5LpZq0"
                "eihoFFKzSElUwxhe9LJ8Pq8wDNOvA0nDYazQitpT0iVffbUetX9d6waKymaiOb23l3p+EH+lUpGZcV8G"
                "gB5HAgBAX0seNrsRHI5r0fI89M5V5BvTnjmTBuIH9MjhG/Sz84/SEftLlV2RIpMkpzCTUz4/oDATzvSW"
                "QNcUi0VVq9X0XrSmIK0fkF70FOknFz5bDxv4ldZVr1NQ3qKoJtnccgB9wXuvOI5VLBYn/IxZUgCgN2S6"
                "vQEAMF/ek8NcLrJWVKb+R8VxSf/5mZfogWg/nX7G13X9jTtULFZUKk98zUJjCEIQLIRrOwEDL+VyUj4v"
                "FbLSS1/wYB3//MdrUHdoTeZWZWtbFWYrqpQjBcEUbzpBnP4/mGuOcbKpMpfwpN+8ebMqlYry+byy2SxB"
                "PgD0KBIAAPpe8qA5166ni/2A2ktdXxs9E7yci5vb1TvblphQ9MyZhoKdytkvtM7fpDPeuq9k+3dl24AF"
                "cXUFVlcQX61QYwqqZXmryuK6sm3Bf5zeNxoXxFTFANP7VfOP6aYKjOXlTfLmG79nvjEzQUsGYLFnAvjl"
                "L3+pt7zlLSoWi3LOKZNZ2kfMud6/4zgmKQEAIgEAoI/1UsCNhfMmeRUVqtl9mGd19KseO3edNVKAS7lZ"
                "5XJZUT1SEAQKw5BgGwB6FAkAAH2tm8MAqGgNALNjLbMdkBwAgO5hAC2AvkXgPT0fNG7xZiaLeeAGsHTy"
                "+byCTKA4jlWr1ab9XRIAANA99AAAgGUsm82SKAF6mJ9hNP5MP+8VlUpFUqNXlnd+0iC/VqtxPwKALqMH"
                "AAAsU1G9rqGhIQXey2VmXXYcwDJjrnNlCWYT4NMDAAC6hwQAgL7XrRal1vH/vdiqFVuskZGRxhdT1EqI"
                "3e4FwPKRXNfWcm3HLUu3eO978n4JACsFCQAAfaufW5E6se1OTrffXmqMx437oxsxAAAAlg4JAAB9y8wU"
                "NwPbbs4GMBfOOxUKhY6sy2TKZCTnvRTHcm76fdTaG2CyBQCmUqlUFNUjmZmcn3jDiC1WGIYzFggEACyt"
                "/nhiBoBJxH3cqt2JHgBxc9Svc05qW58R1AMrBkk8AECCBACAvtet8aTLYSyrud0LgOUjua7HpUldy9JF"
                "/X7fBIB+RgIAAAAAS66f67YAwHKR6fYGAAAWX/KgbXHj72aTN/o5nseBvjRdrx1zjWvbWVtLTxevd++8"
                "zExhGJIIAIAuogcAAMxTP3djdSZ5nsGBFcH3yPXez3VbAGC5IAEAAF3QmeSBk/ONdfVxrgIAAACLhAQA"
                "AMzTfIJ4i3ugGQ4AAAArEjUAAPStxtj28UuneefTbZkuIdC6bTt27JBzbtG3t3397W9vFjfWmXy/bXN7"
                "oYswgMXjm3UAkmu9tdVnsTvjr127VkEmUBRH8t5PvL/53TOn9PPwKQDod/QAAIB5mutDbGyxfOC1du3a"
                "JdoiAJhY48NNUQR0Md12220qlUpLktwEACweEgAAsAhm+8DrnNODHvQgBUGwxFskeTXG/nvnRBEAAEtp"
                "/br1KhQKymQyiiOK/QFAryIBAADzNNceAEmSYI899qCFDMCyki/kFcexqtWqgszSJzgBAPNDAgAAOqyX"
                "psJKpgdj/D+w/Dgb/6DntHRDAcbGxuS9VxiGiurREq0FALBQJAAAoENaW/17KQkAAACAlYFZAAAAAJYh"
                "c+Or/dPRBwBADwAAAIBlxJwUu/FfE/wDACR6AABAR7TOfe2ck/eeYQAAllTsGsF/+vUivGd78dPk682b"
                "N8vMZLFNWgQwjmLFcdz4HYqgAkDX0AMAAABgGYvbegQsFQJ7AOh99AAA0NfmOhXfSuLkxO4BViZzE2sA"
                "jJsCgFgdAFYkegAAWBb6reWp493/+2z/AOhPsTG0CQB6GQkAAH0rDENJ/RP8t25vJ7Y56R0RmxH/AyuM"
                "s8Yy7kHPWpZFlslk0ntOv9yTAWAlIgEAAB3WuQSAl3PJ+pZ8dQB6lLfG0gkU+QOA3kYCAEBf857b2HSS"
                "GgDUAgAAAABPzgDQYZ1sHfNOMqYbBAAAgJgFAEAfc86li5nNeUaATndTbR0fm2zzYrzfXF/jmgOA6aQL"
                "LG++WQcgqf7f2uoz37Rgct9qH++/bt26cfe19vtbbLHMTHEcM3sLAHQRPQAAoIOSB+BOcZ6CXMBK49rG"
                "/DsbPwPgUqhWq5K43wBAryMBAADLlLVMx0WDG4ClVKlUFNWjefXGAgB0DgkAAOigTlbIbjyId2RVAFa4"
                "arWqelSnBwAA9DhqAADAMja4qvkX5+RckvO1tj8BLEfOxrf0JPnApbjyi8WiwjBUGIZL8O4AgMVCDwAA"
                "WKZM44t1AYDUSAQs5QMgvQAAoHfRAwAAVrC4JTfgeWYHlp1YkjlJaSHAZvV+egABwIpEAgAAAGAZMh/L"
                "3O4WeXNS7Jp/79xkJACAHkICAAAgaXxvgMnQQwDoF7Hyhay8d3Ku0QtAzimWyVpLgSziNb1jxw4552Rm"
                "8t4zDAAAehQ1AABgJXIzB/wA+pNXXVbeqofuv1phRvKBJPOypAwg1z4ArFgkAABgmXKzeMo3t3sBsDyE"
                "KitX+ZP2DHcoNMksUuy8nEIpDhrZPyc5ngIBYMXh1g8AKwHdcYEVI7C6BqMRVbbdKatJUb2u2KxZ+C+W"
                "M5Ni6gAAwEpEDQAA6JByuaxcLtfRebIHh1ZJasb/zad9Z83637T6A33LTZfTs1gZk4ayGXlJTr5xvbt6"
                "I/gHAKxY9AAAgA5zrvORN8/8wArjJLlG0i9wgWSRZCYzWv4BYCWjBwAAdFAnK2N3I9EAoPvMS3UnVZ1U"
                "lxT7SIrjxg8sefSrqzk/QEd415gZwMy4NwFAF5EAAIAO69TDr/lGJy9rq/DX+mVrN+LWaf6YIQDoRbs7"
                "bpprvX5jye2e1S92UtT809S8ti15PZ0/AWAlIwEAAB3inJPFjUf0TvQEiBWrMLhKgZy8nKSsIh9Lrio5"
                "ydfbygC0JgNa/h+n7zee9+MDiQljkmf6iG39kJmJAJiB+XHJOa/mdedimdsd8MdS4y/mm9d4LK/GPUHp"
                "Mj/tCcypEpqTfT/pAQAA6B4SAADQYR3rARDVdfihj5L3D0i+0AzIGy2F3prBf+uzePL3ZssiATnQQ2x3"
                "wi3treNimYsV+93Xaxr8txifnKur5TcBACsMCQAAWIa8NWKAjQc8WPVomxSEklUUWNzoG+w0sYXetfyZ"
                "JAtavz/BQlvyaAkEZsenBf0aVf3V6EHjpCiQIr+70GcQ707ueTex03/j9fHungKLaLrkpvNuVr8HAFha"
                "JAAAYJnKOClyGe2sr9JAuFbydXmLG0kAk6LWZsGW1sVYaownduOHALRrf4hvH1k800jjuC0BQI8DYBot"
                "16iT5F2s2FVU91XVnRT5rGQ5SVnJsqp70y4dqKpuUpJs84qXbPbPOJ4+nZAMf5I6Wwx1MtVq1bLZLHcc"
                "ACsSCQAA6BAzk/NOcRw36gEs4UNw7E3KOF1/59169CP+TNu1VtVKRYF5BdZoE6zLdo8ndlJryN46zniq"
                "wNyi8dvf/mt+jh+PDsnANKwtpeZiyeqyqK66l8pyCvIb9MdNNV17/R/17Yt/qa3bbtEuSS6QMvXGNWbN"
                "K9XcNJ17ZqE9ATib+5lzrmut/2EYpuvudgICALqJBAAAdFhHHj69FMl0+he/qy+fIeWbq3TafeOvT/Ky"
                "9i2bLiif7FNMSALMYlNnWg+A8SbU2/RSlJHKkVSR5DNSXJfqUePnQV0K1Lgek9kBFn2bbHwLf3ugH7cU"
                "/ex2AN7t9QNAN5EAAIAO6lgBwLg5kD+QorxUiputf9YYIyw1AoEJr2vbvOkChcmeodtnAphtLwCmHQRm"
                "0FKkc9x1ao3rx5kUZqWCharUYwWBKcyY6pHJTIqj5osleWvMCSAt3rWX3Numusd559MeANQAAIDuIQEA"
                "AF3QkRaouhSZtMs5RXVTNpttfN/HcooVJ9uQRO3NqGK2AYFN1geg5bWN6clmv7nUAACmMdX14ZycMsq4"
                "rCqRFNdrihrRvpyTvHeNup4+mYZ0tv1y5mey1v/Wn9H6DgDdRQIAADokzITp2P/pHpIXQzqNXyxFzQfu"
                "arU6w6vm9mDuZogjZno3o98/sGDOSaa6qs0WfedM8o2L09ToqeNcs+6/d/LNKzNa5Dh8NvezbiYAzEz1"
                "emPgUz6fJ90IYMUiAQAAy9VSP2cvuMmelkBg8SQZtYnXZaeC7pmSm/QAAIDuIwEAAACwTLV3tFmqjjdB"
                "EEz7c+dd12sAUHsAAJZ6IBgAAABWjEadgem/341eAPQ8AIAGegAAQIfU6jX5wHesBWyp18EDNdB9yXXY"
                "Psd9p1u7W+9rcRzL+4ltTN1s/V/quisA0C/oAQAAAIBFEU9R3TO2OK0B0I3kYRxTdRQAJBIAANAR7Q+8"
                "tEQBWE5muqd556kBAAA9gAQAAAAAlhyzAABA91EDAAA6pLX1qxdaohb6IL7Qz0AgACxfXN8A0JvoAQAA"
                "AIAlRw8AAOg+EgAA0GG90PoPAJ3kg92PnJPNEAAA6AzuwADQBbSCAQAAoNOoAQAAHeKcU61WowcAgGUn"
                "iiLVajVlMhnFUTyhiYn7HgD0BnoAAEAX0AMAwHKydu1ahWGosbGxcd39W/VKAVQAWMlIAABAB7Q+9DL+"
                "FcByk9zXwjBUuVxOvz/ZzCckAQCgexgCAAAdRMs/gOXoOc95jqRGcJ/JZAjyAaBH0QwFAB0ShqGcc3r0"
                "ox+tfD6vIAgUx3H6ZzJFFlNlAehlSYu+maWB/imnnKKoHsk5pyAIJryG+xsA9AYSAADQIcmDcT6f10te"
                "8hLVajUNDg7KOcewAAB9IwngwzBUFEV6ylOeogMPOFCxxbT+A0CP44kTADrIYlOhUNDrX/96ZbNZee8V"
                "RdGkLWZYngiO+kPr2HWO2URBECiTySifz+v0009XbPGk9zH2HwD0FhIAANAhpVJJURxJkh772Mdq3333"
                "1djYmKIoUr1e7/LWAcDsZbNZFYtF/cdX/kOPetSjSGICQJ+gCCAAdEihUFBUj1StVpXL5XTCCSfon//5"
                "n5XP51WtVtN6ANLEStqTaW9Vy2QyqtVq6evbkwpL3QqXzWZVrVbT7sHt60vGDPfq+N8wDCU15jMfGBjQ"
                "rl27Jv35ZFprOLT+frValfdecRynn79bku0IgkBhGE7YluTckXYfuziOJY0/t1p/p/0Yt75n68+S70/1"
                "89avW/dT+/5s395kDPpk+7b995Of1+t1mdmEYTfOufSYJZ97su2b7LPOx/DwsEZGRhSG4YR9Ox/t2zPV"
                "9rXu59m8Z+v1nGzrqlWr5L3XN7/xTR13/HGKomjSdQAAeg8JAADooCATKFCj6N973/teXXXVVbryyisl"
                "NQJoM1Mul1McxxoYGBj32vagaLIgKZ/PK4oi1Wq1jj+E12q1dEhDPp+fkMBIttN735VEQHvgk/yZBIJJ"
                "EFYoFDQ2NjYhgJ0pSGt/32q1KqkRPM/2PZaSmaUBXJKwmE5rUF2v19P91Pq66Y7jTO8/WTJgunM22Z+J"
                "mRJO7fu6tWCdNDFBkCQGBgYGVCqVJk0CLKaRkZFJt1NqnJNT1QZp367k80+1vVPt28nuH5MJgkBBEKha"
                "raper2v16tV67Wtfq7//+7/X+vXrVa/Xlc1m0yQXwT8A9DYSAADQBd57ZTIZff/739d73vMeffnLX5Yk"
                "jY2NKZfLqVQqpYFjYi7B42Q9AJbaqlWrZGaqVCrK5XJas2bNuJ/ncjkFQaBisagdO3ZMaDVcTEkwNFkL"
                "8lSJgI0bN+rhD3+4JKlcLiuXy417z/Xr10+6rpkSC1EU6fGPf7y++c1v6kc/+lF67CuVygI/5dzk83kN"
                "Dg7qFa94hW655RYVi8Vx25tIvt6wYYN++9vf6rbbblO9Xp+w/1p/f7JgcrIAvF0mk1EYhspkMhO6kG/Y"
                "sGHc1+3HY2hoSMPDwxooDOiIJx4xIaBv//1ku/fcc0/tv//+Wrt27bif79q1S1deeaX+7u/+btIeEoud"
                "sGpt+U9mCDGzaZMz7ed165/TBd7zTbjl83mtWrVKuVxOT37yk/XsZz9bxx57rNasWZMm+LLZrCTG+gNA"
                "vyABAABdVCqV9OlPfVrvfe97NTY2pl/84hf6/e9/r5///OcTHtjbA8Zt27aN+7parerOO+9UsVhUJpPp"
                "eAIgn8/rkksu0YYNG1SpVLT33ntP+J2BgQFVq1U98MADS759g4OD475OAsKpAvZVq1alQUy5XB4X2LT+"
                "OZX2ICuKojTI+/Wvf63TTjtNUiOI63TwLzVauAcHB/Xud79b69atm9C6PNUQh0qlonK5PCHQT4LV5Ov2"
                "Fuj2zzg2Njbu60KhoDAMVSgUlMlkJiS88vn8uK8n2/9JsmmyhE3770f1SEGmkWQoFosTEg7ValUf+tCH"
                "0nnslzJBJWlc8P8P//APetrTnqZyuaxdu3apXC5P2B/t1q1bN+3XpVJp3NdJj4NEoVCY9v2HhoY0MDCg"
                "tWvXatWqVVq1apXiKJbzTqVSSfl8Xt77Rs8f59N9CwAAACyJLVu22NDQkHnvTZI55+a0SFrQcvDBB1u9"
                "VjczsyiKrNPK5XL693qtbuedd54FQZDuD+/9tMtc99ds9udJJ51k9VrdyuWylctli+PY4ji2KIqsXqun"
                "SxRFFkVR+vPlIPksyVKpVMzM7KqrrrIwDC0MwwWfcwtdvPf23Oc+17Zv355udxRFViqVJmx/P2k9z9rP"
                "ramWRKVSsUqlYt/73vcsm82apPQ6ms11M99jkc1m09fvv//+duutt6b3k2q1Ou56WQ7XThzH9rKXvcwk"
                "WaFQWPC5PNf707p162x0dLQ3C5AAQAcxCwAA9KmkxdPM9MC2B/TGN75RQdCoL9Deetop55xzjs4595wJ"
                "rcnOOfnAp0syvnk5dxsOfKAdO3bo2GOPlTS3IRxLYXBwUJlMRt/73vd0ySWXpN/33vd9BffkPPLep8ts"
                "pvFL6iGUy2W9/vWvTwtAdmJ7W8+Hu+66S49+9KN18y03S9KS9z4AAKxcJAAAoE8lRdFqtZpOPPFE7dix"
                "Q7VaLa1kbl2oOF8oFPSWt7xlQnfjlch5p3e+85164IEHJi3m1mnFYjHdjte+9rW6/fbbFdUjRfVo2hkO"
                "ljMzUzab1RlnnKE//elPaY2KpS4AaM0hFNYyi8GuXbt01FFHadOmTenwEwAAFlv3n0gAAPOSzWYV1SOd"
                "ffbZ+tGPfqR8Pi8zUxAEyuVyXWlZTwKo5z//+R1fd6/56Ec/qq9//euKomjJA8rZiOM4namhUqnomGOO"
                "UalckvOu670TusHMFPhAd911lz7xiU9I2t3y3ulrJwxDrV69Wvfcc4+OPPJI3X333R1dPwBg5SABAAB9"
                "orVFP5mr/KdX/VTvfOc70+r73ntVq9WuFJlzzmlsbExmpquvvlpnnnmmnHMaGRnpeEHCbki6dZuZvvvd"
                "7+oDH/hA2sW8Vz5/azLi97//vV7zmtek0991o8dIJ7UPCSiXy6rWqjrhhBPSaR+Tqew6vS+q1ap27dql"
                "XC6nBx54QA9/+MO19f6tiq1xrGJrFN9zfmJiYiUcOwDA4iEBAAB9IglQEg888ICOP/54VSqVnhxH/+EP"
                "f1g33HCDVq9enQbGy1mtVlM2m1W9XtfrXve6cT/rxc9uZrrgggv0n//5n8pms7J4ZQWSuVxO//Vf/6Vf"
                "/OIXXR1zn+zzKIpUrVZVrVYVRZGe8pSnaNu2bapH9XTKPQAAFooEAAD0Ee+9SqWSzEynnnqqRkZGOjJl"
                "2Xzs3LlTL37xiyU1agP04jYupqSV/8QTT9QDDzzQ5a2ZmZnJe683velNuvrqq7u9OR1XqVT0jne8Q2EY"
                "9kSNBqlxTJJEwF133aVDDz1Ud91114QpLTF3vZgkBYBu6I1/8QAAM0paB733Ovfcc/Wf//mfKpfLPTt+"
                "O5PJ6LbbbhvXFX65tTC3fp5CoaB/+7d/00UXXdQ3nzMZnvCSl7xEu8Z2raheAF/84he1ZcuWtNt/LzEz"
                "VatVbd26Vcccc4x27NjR7U1aFlbKuQ0A0yEBAAB9IpPJKJvN6u6779b73ve+tIJ4Mu1Zr0mmYvvUpz6l"
                "u+++O21pjaPuF8RbDHEcK47idFjG5s2bddppp8k511dV9c1Mmzdv1sknnyznd0/PuByZmaJ6pFtuuUXv"
                "ete70mkzpYk1AqaS/KwTY+/DMNQtt9yipz/96RoZGRl3vc92e7EbCQAAIAEAAH0jiiKVy2U997nP1ebN"
                "m7u9OTOq1WrKZDKK41gvf/nL02JzlWqlZ4riLYT3XlEcyXufznywc+dODQ8P90TV/7n6zne+o3//93+X"
                "pGU75rxeryvIBPrXf/3Xeb9HJ4vuBUGgIAj029/+VkcddZRqtZpGR0f78vzqBSQAAIAEAAD0De+83vrW"
                "t+rWW29VLpfr9ubMKAzDtPjfr371K3384x+Xc06ZTKavWsinkkwjZ2b64he/qGuvvVbee+3YsaNnh2VM"
                "J5vN6l3vepduuummdErJ5SYMQ1177bU655xz5vX6Tgb/SdHPJAnwm9/8Rk996lPTGT8wN/SUAIAGEgAA"
                "0Ce+/Z1v6ytf+Yq8930RnLUHwR/60Id0ww03KJvNqlqtdmmrFk+lUlGQCXTHHXfofe97X5rU6MXhGLMR"
                "BIHK5bKe/exna2RkZFkM1UgCdjNrDNmIY73pTW9SpVIZ97O5vFcnJMFqrVZL63zEcaxf/vKXOuGEE1Qs"
                "FqfcPqYFnBz7BAAa+vMpBQBWkDiO9bvf/U7HHXdc+hDbD13okxoF9Xo9Hbt83HHHpT/rd/l8XsViUccc"
                "c4xKpVI6xCH5bO1jtHt9qVQqymQy2rZtm17xilcoyAR92ZNBmjxYt9j03e9+d9IZD5IClTMF0J0ec59c"
                "Q8n6nHP63ve+p7/5m7/Rrl270qEAUX3iDBskBCaiBwAAkAAAgJ5VqVRUq9VUqVT0yle+stubM29J8BGG"
                "of74xz/qzDPP7NtW8lZxHOuTn/ykbrzxxglDMvox0EimoKvX67riiiv07//+7wrDcNLW5n7RGgAXS0X9"
                "zd/8zYTv92KAnGxT63kURZHiOJb3XhdffLHe+MY3qlqtNnoH2OwSGCsZ+wQAGvr/CQwAlikzUxiG+uQn"
                "P6nrrruu25uzYFEUqVKp6LTTTtN9993X7c1ZsLvvvluf+MQn0t4Ny0FrEuCNb3yjfvvb32pgYKDbm7Uo"
                "zjvvPG3durVvhtC0y+fzkhrXkSSdf/75OuGEExSG4bKoqdEJ/ZiYA4DFtjyeWABgGWgPSrLZrH7yk5/o"
                "M5/5TJe2aHHVajV57zUyMqI3velN3d6cBXv605+eTslWKpW6vTmLJkkCSNLznvc8lUqlSbuY95vTTjtN"
                "YRhqYGBgXCDYL8mAcrmcJgGS6Qu/853v6K//+q81MjLS5a0DAPQLEgAA0AOSIKR1eq/t27fr2GOPTR/u"
                "J+u2vJBlMbZ5rutLAsvvfve7Ou+b56laraparfZFVfPWceJvf/vbddttt6lcLqefqdP7fykl23f33Xfr"
                "pBNPUrVWTc/NpJheL0sK6CXj50877TRt375dtVpNxWIxrUuR/O5kLcMzHa+lrskw2foqlUpaVyOKImWz"
                "WZ1zzjn66Ec/qnK5nL52ufRImc5cr7fk+gWAlW75/wsBAH0geXCv1+uK41i1Wk0nn3yyRkZGNDg4mAaZ"
                "y8m7T323SqWSMpmMMkGm5x/Oq9WqnHO69tprddZZZ3V7czoim83q4m9frM9+9rOKokhRPUp7PfS6bDYr"
                "55y2bNmiz33ucxN+3uvn20yS+8XAwIA+/elP66yzzpJzblnMsAEAWDq9/y84AKwwxWJRX/3qV3XZZZdJ"
                "ak43FwRd3qrFd8899+gd73iHJMl51/MzG+TzeY2Ojur4449XuVzu9uZ0RK1Wk5npH//xH/XrX/9aQaZ/"
                "zsOkeOEJJ5zQ98H+ZJJW7WKxqCAI9M53vlOf/vSnlcvlVsz5CQCYOxIAANADzEzValWZTEabN2/WW9/6"
                "VtXr9bRHwHLsARBFkS644AL99Kc/bdQHcL1fnO3DH/6wbr/99p7vAr8YgiCQmSkIGtMBHn/88br//vv7"
                "YriG1EjY/OhHP9KPf/zj9LP0yxCM2UiSglEUpb1TTjvtNJ177rlprYDEcvi8AIDFQQIAAHpAHMXKZrOq"
                "1Wp61rOepUqlko5ZXY7Bv9QI0KrVqk466SSNjIwoyARyzvVUsJK0skrSL37xC33uc5/T4OBgl7eqM+I4"
                "lnMu/XPr1q36q7/6q57vZp5sW61W03ve857078tN+30hk8koiiK97nWv01VXXSUz086dO9N6AsstAQIA"
                "mB8SAADQZVE9UhQ3Hubf9KY36U9/+pOy2WyXt2rpVSoVRVGkLVu26EMf+pBqtZpKpZLiqDda16N6o2W1"
                "Xq9rZGREJ5xwgqIoUqlU6osx8IutVqvpyiuv1Omnn67A995QgPakxLe+9S1df/31CoLdiaXlHAAnScN6"
                "va6jjjpKv/jFL7RmzRqNjo6uyPMVADA5/kUAgC6K6pHqUaOi9yWXXKJvfOMb8t73TTfrhUh6N1QqFX3p"
                "S1/Stddeq0Kh0DPjzINMoEyQSbtW33PPPQrDMG0VX2mSyvPvfe97deX/u7Ln9kE2m1W1WlU2m1WxWNTb"
                "3vY2lcvl9PvLmfc+HRJQq9VUqVT0F3/xF7riiis0NDTUc8cKANA9JAAAoAvMLG35T8b4v+pVr2pUWl+m"
                "Xf4n01pR/pRTTtGuXbt6Zs55M1OQCfS///u/Ovvss1WpVFQul5dld/LZCMNQUmO/vOpVr9K2bdu6vEUT"
                "hWGoqB7pM5/5jB544IE0+C8UCt3etCWV3ENyuZycc+lwouc+97lpMVEAACQSAADQFc45BZlAYRiqUCjo"
                "RS96kcbGxlZUcNnaLbtWq+mmm27Sxz/+cQWZoCe6aDvn9MADD+h1r3vduBbkbm1ba/f1bnRpT2YECMNQ"
                "9957r974xjem52uvtLDHUayx4pj++Z//Wd571et1mZkqlUo61Way9Lv2z9Jam6FSqaRJgBe/+MW67rrr"
                "JCk9d5bD5wcAzA8JAADoklKpJOecPvaxj+mKK67omSCqWzKZjD796U/r2muv7ZkA5U1vepN27NjRE9Mw"
                "to7j7laXbjNLg+r/+q//0tlnn52OO+920iaOYznv9Pd///cr7lqa7HppTQY885nP1KZNm9LhRd0+VgCA"
                "7iEBAABdUigU9Jvf/Ebvf//70+7VK5lzTpVKRW94wxt6ogbCJZdcou9+97uq1Wo9MSwjjmPlcrlxwya6"
                "JWlJPvXUU/W73/1OAwMDXe+94r3X9ddfr7POOqsnjlc3tbbyR1GkHTt26HGPe5z+9Kc/yXvftQQbvQ8A"
                "oPtIAABAl+zcuVMveMEL0nnW0XDdddfp85//fMfX294q+va3vz0NJHuhB4AkrVmzRnEc90TCKI5jjY2N"
                "6aUvfamKxaKk7s43X6lU9MY3vjEdB7+SJcNCWmsfPPDAA3rMYx6j7du3d+V+03pu0AMBALqHBAAAdEjS"
                "bXtkZERmplNefYruvvtuRVHU9RZdqdE6l8lklMlkOrK+9jHstVpN3ntFUaT3vOc92rRpU0e2o1Ucx6rV"
                "anrTm96kzZs3q16vyznXtRbl1v2zbt06XXPNNXr5y1/eE1Xds9msnHO66667dMIJJ3Rl6so4jhvTSdYj"
                "XXnllbr66qsVx3FXAsz289l7LzNTLpcbN/a+U63gzjmVy+V0fXEca2RkRE996lO1a9cuVSqVtKdNJwpv"
                "Wrx7H5AAAIDu6f4TJwCsEPV6XZI0PDysb3zjG/rOf39H+XxecRz3REDnnEu7u3crgEr2hZnpNa95jWq1"
                "Wsf2TxK0/fCHP9S//du/qVgsdnXO+KQFN+n2f/bZZ2uvvfbSGWecoT322ENSIwjv1pCAZNx/qVTSD3/4"
                "Q/3rv/5rGnR2QhLc5nI5jRXH9Na3vlXee9VqtQkt3J04hs45BUGgxz3ucel1nWxnPp9f8vXPJJPJqFar"
                "6Y9//KOe/OQna9euXWnirROFN2PbfQ2TAACA7iEBAAAdEvhGN/I//vGP+tu//duuBdpTOfHEE7XPPvvI"
                "OaeBgYGubUeSCPjBD36gb3/7242W1Hjp95P3Xjt37tSJJ56Ybke3j0+9Xle1WtXznvc8Pfe5z1Umk9Ga"
                "NWv0wx/+UM451et1hWHY8QSSmSmKGlNYeu9VrVb1zne+U7/+9a+Vz+c70qKcy+VUKpUkSV/5ylf0+9//"
                "Pt2ebgwBCMNQGzdu1BVXXKFjjz1WhUIhHTrSzZoWrT0AknPld7/7nZ7znOc0pt2Mokm3bylmmaAGAAAA"
                "AOZty5YtNjQ0ZN57k2TOuTktkha0HHzwwVav1c3MLIoim0m9Vrd6rW5Pe9rTzDln2Ww23e7kM0y3zPXz"
                "zXUZGRmxc845xwqFgg0NDS35/ptpyeVytu+++9rtt98+6f6M43jGfT4XcRzbS1/yUpM0q+Ox0GU2+9d7"
                "bxs2bLBNmzaZJFWrVSuXy1atVu2jH/1o+jthGC75+THV8Q+CwHK5nIVhaGvWrLHNmzen18VSKpVKZma2"
                "ZcsW23PPPU2SDQ4OpueO996890v++ZN9v2bNGjv99NOtXqvb6OionXzyyTYwMGDeewuCYEm3Zbbbm8/n"
                "TZJls1nz3ttjH/tYu//++61cLlscx+OuqeTr9u/PV7VateOPP96CIEjvfZ1c1q5dayMjI72TcQUAAMDc"
                "3HfffTY4ONiRYHSyZTYJgOTnpVLJSqWSve9971u0h9+FBgRhGKbb8pOf/MSiKLJ6rW5PeMIT0iCqmwmA"
                "gYEBk2THHHOMVSoVi6Io3c9RFC0oQInjOH2P5M8LL7zQcrmcBUHQkc840/EZGBiwIAjsnHPOsUqlMmng"
                "cuSRR1oQBDY4ODjnAHOxP0c2m7WBgQF7xSteMe6YVCqV+caM0yoWi2Zmduqpp5qkNMhejGtjLvswuYbW"
                "r19vO3bsMDOzcrlso6Oj9sQnPjENupPzarGu34UetzAMLZ/P21Of+lTbtm2bmTXuU9Vq1Uql0oTra6EJ"
                "ARIAAAAAWJBeTwAk36tUKlav1e2Xv/ylDQwMpK2UC10WGkAkgcnHPvYxq1arVqlUrFQq2XXXXWfe+7RV"
                "t1sJAGl3S+4FF1xg5XI5bfWtVCoLDkhaX3fffffZ0NCQSbsTD0v9OWeToHn1q19tY2NjVq1WJw1ctm/f"
                "bgcccIAVCoWOJwCmer8wDO3888+3eq2+ZMG/WeMc2LJli61du9by+XxHW9iTVv1sNpt+9ne9610Wx3Ha"
                "Q0OSRkZG7JBDDrFsNmu5XM7y+byFYbgo1+9Cj18QBBaGoeVyOTvmmGNsZGTExsbGbOfOneOuDxIAAAAA"
                "6Am9ngBIxHFsW7ZssX322WdRu5YvRgDxjGc8w6RG13KpEVCamb3xjW9Mu3Z3KwFQKBRsYGDAnHO29957"
                "27Zt28YFHwsNSMbGxtK/P+c5zzFJaav7ZJ97sT/fTMdnzz33tO3bt08ZsJTLZZOkq666yiR1PQHQGhQP"
                "DQ3Zpk2b0sCvWq3O+fjMxutf/3oLwzDtap/sh8W6RmZKAjjX6PlQKBRs27ZtViwWJxyvbdu22WMe85g0"
                "4M7n84uy/oUev9YknyQ76aSTrF6rW7lcHtfjJllIAAAAAKCrej0B0Nq9/AUveIFJSlsBF2P9Cw0g9txz"
                "T7v//vvHPRCXSiUbGxuz+++/3/bbb79xAUKnEwDJknTtfvOb32xmlrYsL9YY5XPPPTf9fMlnbR0G0K0E"
                "wLe//e1ZByuf+tSnup4ASHpOJAH4fvvtZyMjI/M+LjP5yU9+kiZs2oPqxbpGZtp/YRia994+8IEPTHqs"
                "KpWKVSoV27p1qx166KHpti5GzYbFOH7JeZ70fnnNa15jxWLRyuXyhARAexJgrkgAAAAAYEF6PQGQdFc/"
                "88wzOxKAzSVo8N7b//7v/1qpVJrygfj73/++SY2kxWTr6/T+DsPQfvCDH5hZY/z3fAOS5Her1ardf//9"
                "aeA61/272Mcv2c/eezvllFPmHKg88YlPNEk2PDzcle1Piu4lSxiG9opXvMKiKEqvhYWoVCppYFqtVu1x"
                "j3uchWE4YWz9bI/fYgTgAwMDduCBB057HSU2b95sBx54oEma15CNxTp+Ux235OdveMMbbHR0dFwPmXqt"
                "PmkvgLlcfyQAAAAAsCC9ngAwM7v55pvHVfvvZgKgtQL4e9/73hmDllKpZK985SstCIIl2f65Lvl83g4/"
                "/PB0TPx8EgClUikdl14qldKu//PZv4t9/JLv77333vMKVLZs2WKrV6+e9bmx2NvfngDIZrMWBIH927/9"
                "m9Vr9QVXkk+C0CiK7JJLLpk2+J/tPliMAPxb3/rWrI/V5s2bbd99902HLPRaAsC5RiLqDW94g1WrVSsW"
                "i+NmdJguCTATEgAAAABYkF5PAIyNjdlDHvKQjgVgMy3J1F+HHHKIjY2NzepBeMeOHTY8PDxpl+VO7+9k"
                "Gz7+8Y9PGozMJI7jtBW5UqnYRRddlAY889m/i338ku9dccUV8w5SLr300vRYdzsBkByzMAzt6quvXnAd"
                "gEqlYtVq1UZHR+1xj3vctMH/bI7fQpcgCOwZz3iG1Wv1WfUAqFarFsex3XrrrbZmzZqeSwC0Jiol2Sc/"
                "+UkzMxsZGRk3K8BUSYCZkAAAAADAgvR6AuDEE08059yUXbIXuv7ZBAmtQYYkW716td18881TTivXKplm"
                "7Zxzzpk0WOn0/k62Yd26dXbXXXfNKwGQBJJ33nmnrV+/flzvhrnu38U+ft57e8Mb3jDvAKVYLFocx/b6"
                "179+yvOtkwmAZN+GYWgPfehD0yKO85XUffjyl7+cngtz2b7FWFrfN5vN2q9//etpZ2lolUwFGkWR3XXX"
                "XT2VAGj9TMnfwzC097///en11dqLYz41AUgAAAAAYEF6MQGQtHJedNFFEwKiZFmqB/mpghVJNjg4aPl8"
                "fk7dlaVGq2W5XLYnP/nJJu0u8NaNB/jWIOUZz3iGlcvlccH9TC2ScRynx+cv//Ivx03H2I0EQBiG6X4M"
                "gsA2btxoSWX/+RgdHU0LJB5yyCHpehZz5onp9s9U53tyzh977LFpID+f6QGr1Wo6m8Z8tm+xgv+kUORr"
                "XvOaeR2rcrls5XI5LWLYHoQvdQJgqv3T/r3k3PnIRz6STm+Y3OfoAQAAAICO67UEQNLF984777TVq1d3"
                "PQGQjPlPus6fdNJJs2qpTLROaXbHHXeklda7sa/bP3M2m7Wzzz47DUwmC0qmcvbZZ88qCFnqACw5NkND"
                "Q5bP5+36669fcHCSDO245ppr0nX0QgIg6WJ+9tlnm5mNS97MxUc+8hHz3luhUFjw9THXJZ/Pp1P5NZNH"
                "khqV/ud7vC6//PIpa4R0OgEw2fsnPQI+8pGPmJnZzp07SQAAAACgO3otARBFkRWLRXvYwx6WBl7dTAAk"
                "QZkkO/DAA210dNRGR0fn/ACcJA0+85nPWKFQmHLMfKeW5LOtXbvW7r77bjNr1FuYKSCpVqt211132bp1"
                "68YFIFMdg04kAJJu8v/4j/9oUqMVf67HZyqf//znTVJacG6pjsNsEwDJ71x33XVTFs2czr333psms6aa"
                "uWEux2+uS+s+/Jd/+ReTFhb8j46OWrlctu985zvz2t7FPn6THcsk2ea9tw9+8INp8F8ul0kAAAAAoLN6"
                "LQFgZvba1742rX7e7QRA8jtBENhVV11lSYt+tVqdVQ2AdpVKxZ7whCeY1J0hAO2fPSnClgQfkxUpaxXH"
                "sR1yyCGz3u+dSABIskc+8pHjjsVChgG0vrZUKtmLXvSiJT0Gc0kAJImjhz70oeOmmJutV73qVeNqCyz0"
                "+M11SdZ74IEH2vbt2+d9jCZzxhlnzHmbF/v4TXUsW19z5plnWhzHNjo6Sg0AAAAAdFa3EwAPechD0nGx"
                "5XLZvvvd76YPt5MF+t1IAEiyL3zhC4v20JtMa9itfd66JK3A5513npVKpTSobG+ZTLqbf+ADH0jnp5/N"
                "/lvqJdmGW2+9dUFj/6dSqVRs69atls/ne6IHQDIjgHPOXv7yl1u9VrdisThuasb2hE2SXLvmmmtmTKR1"
                "4ngFQWAXXHDBkgSRX/ziF9OpDSfbv51MAEx2v0ped+6555qZpcnPSqUy6cwAJAAAAACwqLqdAHjMYx6T"
                "Bp2bN29OxyVPFZx0IwFw5JFHzqu1fzrN4mddXwqFgjnnbGhoyLZt25YGGa2SMcs///nPLZ/Pp8mLbgSQ"
                "ky1nnXXWkgckl19+eU8kAJLfGRwctDAM7Vvf+lYaQE5VEyAJMo844oieSAD8xV/8hY2Ojs56Gs25eve7"
                "353W7uh2AqB9CYIg3bZvfetbVi6X06KTyQwNMyUATjjhBAuCoCvDiEgAAAAA9LluJwAOOuigNHB52tOe"
                "ZpLSYmfJNnUzAbDPPvvYvffeu6gPvMlUZrOtxN6p5WUve5mVy+VxXcuT4LFUKqV1GZxrjGlOWqK7uRx5"
                "5JFpUcal6AHQ6j3vec+iXyfzSQA459LZF5IaDknxzMl6AMRxbD/+8Y9nNZRmqZd8Pm/XXHONlUqlJTlW"
                "lUrF6rW6feADH5jV+bnYx2+u67v00kutXqun0wPOJgHwile8ggQAAAAA5qfbCYCNGzeamdknP/lJC8Nw"
                "3DhnTRMgdSoBcMkll5jUCNoXa58nvQmuuOKKruzz9s/f+ucFF1xgY2NjaXfyYrFoZmavf/3r09ckvTS6"
                "EfAHQTDu602bNqXHZS6zM8xFcuwrlYodeOCBi77/55IASOpiJMfBe2+PfOQjrVqtTloUMIoiq1Qqtt9+"
                "+01aU6MTx6x1PSeddJKNjY3ZyMjIkgzZkHbPvHHSSSf1ZAIgSW4GQWADAwN26aWXpsOgWoP/yY5ntVq1"
                "E088cVxPgk4uJAAAAAD63JYtW2xoaCgNKjod0D396U+36667ztauXTurFrulDmCSfSDJ3v3udy/5g24S"
                "WCefTV1OCAwPD9vo6Oi4scm//e1vlyzYmOvxyeVyaYLo7LPP7nggcvvtt1sul0sDuE5//vaAOplS75RT"
                "TrEdO3ZYqVSaEDB+/vOft2w2mwaenVySpEUYhrZ+/Xq76aabOnbMqtWqPf3pTzfvvQ0MDPREj5XJ9k8u"
                "l7Nrr712QtCfJARa1Wt1O+mkk8x7n04p2sll3bp185oFBQAAAD2i2wmADRs22F577WWS0sBqpgfmpUwA"
                "JMFla9fypd7/s5mOrZPLiSeeaJVKJQ0oDzroIJOUFv5bzGW+x+foo4/uShBSqVTsq1/9qkmN1tC5ft72"
                "ZaHna2sS4ktf+lI6ljwJFrdt22Zr1qyZ1bW1FEtSPNF7b29/+9sXvZbGTIrFoh1xxBEWhmHa06mXluTY"
                "rVu3zm6++eZ0KtSp1Gt1e+UrX2ne+7R+RycXEgAAAAB9rtsJgNZK1u3duydbOtEDYHBw0O6///4lK1LW"
                "qlqt2le+8pWujOedbAmCwIIgsF/+8pdmZkkviDlNHTeXZT7ny+DgYFeDkEqlYs961rMWpcfGQs/XpCU4"
                "eb/bbrvNyuWy7dixw6Iosle/+tUWhqENDw935fpOqtVv2LDB7rvvvo4nAEqlkm3fvt0OO+ywnuwBoGZi"
                "LQgCW7NmjW3evHnaJEC9Vk+nciQBAAAAgDnrdgJAcwyIljoBEIah/exnPzNp91jipVSpVGxsbMye97zn"
                "LUmAPdcl2QePfvSj7aKLLrKhoaFxrbhLsb7ZHPPWry+99FIzsyUrJDeTarVq9913n+25555dTQAk79F6"
                "XDZu3JhW2L/88svHdX3vRtG/ZN2f/OQnu3KsktkRyuWyHXrooR3//LM5hsnwjCAIbMOGDWkSYLIigPVa"
                "3U4++eR0WEOnt5cEAAAAQJ/rdgJgrstMRdLmsrS+Z/Iw3ulAZWxszKrVqt19993jupQvRXf7XlxmEyAl"
                "52Yul7OTTz7ZyuVyx1uS25VKJfv+97+fXjvzTY4sRgDZvhx33HE2Ojpqhx12mGWz2a5V/E+urb322svG"
                "xsY60qNmKuVy2YrFYnqNdatHxEz3tHw+b/vvv79t3rzZqtVqWovDrFGQkwQAAAAAFmQlJwDag7bHPvax"
                "6YPtyMhIR1uYx8bG7LOf/awFQWCFQiGdEUHzCCr7aZnpeLcmQh7ykIek0xSOjo52pEbDdEqlkr33ve9d"
                "ULJmoddD+/vlcjnL5/P2rGc9ywYHB7sa/DvXGAJw0UUX9UzAeOONN9q+++5rknqiJkD7/SibzVoul7OH"
                "Pexhtn37disWi2lhx2q1apVKxV75yleaJIoAAgAAYO5WegIgmU5reHjYNm3a1LVu5VKjlfIJT3hCGsz1"
                "wpCApV5mOt7JfvDe280339xzgUe5XLYjjjhi3PR8c1kWej20v19SUyMJvrsZ/Dvn7IgjjrByudzV66rd"
                "9ddfb3vttVdP1ASYKgGQy+Xs4IMPTqfkHB0dTffjiSeemB7rTm8vCQAAaPDd3gAAwPxEUaRaraYvfelL"
                "2nfffeWc6/g2JMFRPp93X/3qVzU4OKgwDBVFUce3pVckxyGXy0mSTjvtND34wQ9Wt7v+t3PO6YILLtDg"
                "4KDiOO76ttRqtfTvURR1fJu8H/9IdNpppymfz7tCodD5C2sSlUrFHvWoR7kLL7xQmUym25szQbVaVaVS"
                "UaVS0aZNm3TUUUdJkoIgUK1Wk/de3ns55ybsawAAAGBGK60HQDabTaumJz0A3vCGN5i0OxDvtlNPPXXc"
                "7AjLeWk/vsn3k+rxkuzwww+3arVq5XK5J45Pq3K5bGZmF154YXpOJRXau9FCO9n+7OT6WnsgPPe5z+25"
                "49U6bOSSSy6xfD6f9gJSy/Gbax2RpbqfFQoFe+ITn2ijo6Pp9I4nnnhien10+nyiBwAAAECfW4kJgIGB"
                "gXRe9EMOOSR9mO1mkbJEpVKxbdu22cMf/vAVOwRA2l34L5vN2u233271Wr3rY/6nkiQm3vKWt5jUGIef"
                "TKfY7eul00tSD8F7b9dee21PHq9Wl112WXqsBgYGei4BkMvlLAxDe97znpfWAjj++OPTe0Onjy8JAABo"
                "oA8WAPSJKIpULBZVq9WUy+X0ve99L/3ZqlWrut5N2cy0xx57uDPPPHPFDQFwzqVd/81M2WxWn/70p7Xv"
                "vvuqHtWVzWa7fnwmk8/nnSR99KMf1d57761arbZih3Akn/nNb36zHv3oR/fk8Wp11FFHuYsvvliFQqHb"
                "mzKpSqUi770uvfRSnXDCCTIzrV69WlEUKZvNdnvzAAAA0G9WWg8ANVtos9msnXPOOSb1Ttf/VuVy2Y4+"
                "+uiut9Av9dJ+fJP50CXZscceO67rfy8OAWivSXDddddZGIYrtgdANpu1NWvW2LZt23ruWLVr7VFywQUX"
                "jJs1oRd6AARBkBYqTO5db3jDG+x5z3teeh/r9PGlBwAAAECfW2kJgORzvvnNb+6pyuRT2bBhg0lKxygv"
                "t6X9+CbfC8PQ7rzzTuu1on8zqVar9rnPfS49ZosRJPbqkgSpanb5TyrYn3baaT07XGM6H/nIR0xSOoyh"
                "UCh0fQjAVOuT1JUEEwkAAACAPrfSEgDZbNYOO+ww27FjR18El+eee25auHA5FgZsP77J984555x07vNF"
                "3aEd8tSnPjU9X7t9zSzlouZxLBQKJsn23ntv27lzZ98cs2KxmE6zJ0lveMMbxl1vvZYAWOz1z3UhAQAA"
                "ANDnVloCYGhoyO64446+eYAtFov2jGc8w3K5XNeD9aVYJgson/vc51q5XO7b4F+Stm3bZuvWrVv2CYAk"
                "8E+O3XnnnWdSbw6rmU5rMvBxj3tcOjMACYDxCwkAAGigCCAA9Imzzz5be++9d7c3Y9aCINDnPvc5hWGo"
                "IAi6vTlLbmBgQOeff35aWK8fjY2N2apVq/S1r32t25uy5CqVioIgkJnp0EMP1Utf+lJJ6rtztbVg409+"
                "8hM9/OEPV7Va7eIWAQAAAEug33oAzLUFTS0tzW9/+9v7ruUqaQX/8Ic/nI65zmazVigUrFAoLHj/qQd6"
                "AajZhTwIArv88sv77hhN56STTjJJNjw8bNLc55nvtRbg9iWpAVAoFOzKK6/s+2OXFJ28//777YADDpgw"
                "FWe39/diL5rjdbp27VobGRnp++MMAACwYq2UBMATnvCEvuy6mlS+Hxsbsyc+8YkmybLZbFqorNMBwGIv"
                "yWfJZrP2tre9re+Oz0y2bNli++23n0mNom3LLQGQnIfHH3/8sjh2ydCTOI5t27Ztdthhh6XF9tSH98fF"
                "vv5JAAAAAPS55Z4ASCqT33HHHX09prxSqdj//d//pbUAkqC50wHAUi177bWXbd++vW+Pz3Quv/zytMfG"
                "cksAqJnYuPHGG5fVsatWq1YqlWzbtm22YcOGRbveem0RCQAAmBdqAABAj3Bu/NDxarWqL3/5y3rwgx/c"
                "t2PKJcnMdOSRR7pXv/rVymazqtVqqtVq3d6sRfONb3xDa9eu7etjNJWnPOUpete73qV6vT7u+2b9H0cF"
                "QaA3vvGN+vM//3OX9FZZDuI4VhAEWr16tS677DJt2LBhWV1vAAAAWKGWWw+AZKq8ZEz5a1/72mUTlEjS"
                "6OioDQ0NWaFQsIGBgY63AC50aR26kHz98Y9/fFkdo1aVSsXqtbpVq1V70YtelH7+MAz7sgeApHFDa9as"
                "WWP33nvvsj5+ZmY33HCDOdeY9aB1Os5u3/86ff3TAwAAAKDPLbcEQD6fT7vJH3nkkcvuQbVardp3v/td"
                "y2azNjw83PEAYLGWJJh62tOetuyOUbtkirnNmzfb0NCQDQ4OLloSoBvXW+t589GPftTiOO7r4TXTqVQq"
                "Vi6XLY5ju/TSS825Rt2D1n3Q7XtgJ69/EgAAAAB9brklAIIgSMda33rrremD6nLpnjwyMmKlUsmOPfbY"
                "RTle6nDgn8/nzTlnuVzO1qxZY3feeWd6XFrnYl+uLr/88nQ8eTab7bsEgFp6ceyzzz42OjpqY2Njy/64"
                "VSoVq1QqdvHFF1sYhjY8PNwTNRg6ff2TAACABmoAAECPyGQyKpVK+vrXv66DDz7YJS2T+XzeLYdAZXh4"
                "2AVBoM9+9rPK5/Pd3pw5K5fLcs4pCAKddtppOvDAA9Nx/7lcbtnVAEjOuWKxaJL01Kc+VW95y1tkZgqC"
                "YNLXmFm69BrnnGq1mpxzetvb3qahoSGXyWS6vVlLrlKpKIoiPf/5z9eXv/xlxXGsMAy7vVkAAADA3PR7"
                "DwDnXDq9mtSoSH788cfbcmnxn0ypVDIzswsvvHBcq3onWgAXuiTH64UvfOGyPT4z2bp1qz3mMY9Jh6pI"
                "mnVrcrd7ACTrfOQjH2krocdGu3K5PO7aax8SoT67h2qO1y89AAAAAPrcckgAJGOpJdnBBx9sO3fuXPYP"
                "qKVSyarVqj3pSU+yIAhsYGBgXsdPHU4AZLNZW7t2rd13333Ldtz4TKrVqt1111221157pQmc1mRA6zJZ"
                "AN7tBID33r73ve+t2ONXLpctiiI7/fTT00KcYRhaEARdvxcu9fVPAgAAAKDP9XsCQGpU/FczuLzhhhvS"
                "h9PlHKAkXctvvvlmGxoasmw2a7lcbskDgIUuzjk7//zzl+1xmY2xsTGrVqt28cUXTxroq21/TRaAdzMB"
                "cNRRR1m1Wl2xCQCpUROgWq3aBz/4Qctms30Z/M/n+icBAAAA0Of6PQGQtLyFYWhf+tKXTFrexeTag65q"
                "tWrvfve700TIUgcAC11OOeUUkxo9GJZsJ/WwJHBMjuNxxx2XzuaQJHDUQwmA9m0IgsCuu+66dGrDbu7L"
                "bisWi2Zm9qpXvWrK49Xri+Z4/ZIAAAAA6HP9ngDIZrPmnLNjjz12xQYk27Zts3322SftBbGUAcB8lqRq"
                "/MaNG1fk8ZnOzp07bcOGDea9TxM46pEEQPt2SLJ3vOMdViqVVuT4/8lUKhWL49hOPvlkC8PQ8vn8tMev"
                "1xbN8VomAQAAANDn+j0BIMk2bNhgY2NjK2I6ssmUSiW77LLLLJvNznkssjqQAHCu0VPjpz/96Yo8PjO5"
                "/PLLbXBw0CSl16Fa9l23EgDJ+RGGoYVhaKtXr7bR0dH0GK7UhFurcrlsxWLRisWiPfvZz06vvyAI+uJ+"
                "KhIAAAAAK0u/JwAGBwftZz/7mZnZiuwBkLTEFotFO+644ywIgjn1AtASB//JtrzjHe9YccdmNpLZKj7x"
                "iU9YLpfruQSAcy7twfGxj32M4L9NtVq1eq1upVLJtm7daocddphJslwuN+feOCQAAAAAsOT6PQFwzjnn"
                "pAFwl3dlVyQJgGq1aps3b7a99947bYXULI6nlqC1v/Vr770dfvjhKzI5M1dPfvKTey4BkKxn48aNHMMp"
                "JEmcYrFo9913nz35yU+ecOzav+6VRSQAAAAAVpb2BMBMy2IHkAt5YD3uuON4EG3zzW980yTNuwuyFikB"
                "4L23oaEhGxwctM2bN5u0cgv/zUa5XLaRkZF0OkdNcew6nQAYGBiwXC5nl1xyCcdulrZu3WoHHXRQOjNH"
                "ci1qCZIAWuD1OteFBAAAAECf67cEQNIdee+99zYCyomKxaIdffTRaRDejYCitTfJ5z73OY7RLFQqFSsW"
                "i/bf//3f5pybckrHTicAgiCwI444wlZqD5v5+tOf/mR77bWX5fN5KxQK5r23MAxJAAAAAKC7+i0BkM1m"
                "rVAo2G9/+1u6JE/hrrvuSovKdTMB8IIXvIDjMwfVatXGxsbsda97nUmTz+jQjSKA11xzDVX/Z6lcLlu1"
                "WrVyuWy33Xab7bnnnpbNZpdsiJVIAAAAAGAuej0B0P473nv7zGc+Y2ZGq+QUyuWyffrTnx4XIM52ZgAt"
                "UvC/evVqu/HGG0nSzNGOHTts+/bt9shHPnLSY9OJBIBarrlXvvKVHL95qlQq9vOf/zy9NvL5PAkAAAAA"
                "dFc/JACSJQgCO+qoo0yiCvlUyuWymZmNjIzYn//5n1sYhlYoFCybzXbseEqyr3/96xyfeSgWi1av1e2G"
                "G24Y12VcLft3KRMAyXqy2awNDQ3Zpk2bTGoEs/QCmJ/LL7/ccrlcmsBJagIsxpAAkQAAAADAXPRTAmD9"
                "+vW2detWHj6nUS6XbWxszOI4tt/97ncWhqENDAxYNptNewFoCY+nJHvhC19Iy/8C7Nixw6rVqn3oQx9K"
                "a14kc8svdQ+ApPaAJHv3u9/NMVwkF198cZoAaE/okAAAAABAx/RLAiAIArvhhhusUqmkxf8oAji1JAB/"
                "//vfnwYe6sDx3HPPPW1kZMTMjBbjBRobG7PjjjsuTd7k8/klTwCEYWi5XM72228/2759O8dwESTXwwc+"
                "8AGTlNYEmO2wHBIAAAAAWDS9lgBo/56aD8wf+MAHLI5jS+bclkgATKd1P+2///5pF+T2ZbGP5/e//32T"
                "Gl3GO/JBl7mxsTFbv369SbJcLrfoCYD290h6GXzrW9+acBw5pvOTJC3L5bK9613vShNyi3H8RAIAAAAA"
                "c9FrCYCkFVJqFM2SZC960YtMYtz/fN1+++3pfOTttQAWejzDMEyP12mnncbxWQI//vGPLQxDy+fzFobh"
                "oiYAkvHoyVR1QRDYxo0bmWJzCVSrVSsWi3byySen0wIu9BiKBAAAAADmotcSAElAks1mLQxD22effdJq"
                "/1T9n7tqtWpmZmeddVYacCRJgMm6IGuOxy85b4488kiOzRI6/fTT0+uitRbAYrYgh2FoQ0NDds0115iZ"
                "kQRYApVKxcrlsr30JS9NjyMJAAAAAHRMLyUA2r+Xy+Xsyiuv5GFzgZLhAK94xSvGHetCobAox3PPPfek"
                "OOMSq1ardvjhh6eJscUcApCcB5LszW9+s1Hxf2kl1+NRRx214CSASAAAAABgLnopAZD0AEhapr/whS+Y"
                "1Cii1aHdsazt2LHDXvziF0/bgqw5Hr/99tvP7r77bo7PEkqC8fvvv9+Gh4fH9QJYaAKgdUjIoYceajt3"
                "7uRYLrFkKNPOnTtt/fr1JAAAAADQOb2WAMjn8+acs5e//OU8ZC6RN7/5zelQi+QYZrPZtDq5JjlOScIg"
                "Sc547+2JT3wix6jDrr32WhsYGDDn3LiW+ySYnylgTIpBJscxmYt+w4YNdvfddzN9Y4dt3rzZDjzwwHHH"
                "kQQAAAAAlkyvJQAk2caNG210dJSHzCV0ySWX2Nq1a8fVA0jqAyRdzJPvqSUJEIahrVmzxv7lX/6F49Ml"
                "11xzjRUKhTRxk7Qgz2ZYgCa5BvP5vN10000czy4YGxuze++919auXZsmY3o5AbBu3ToSAAAAAP2s1xIA"
                "w8PDdsMNN/CA2QF33323/e3f/q0NDw9PCCY1SQ+AtWvX2rve9S77wx/+wPHpklKpZFEU2bXXXmsbN240"
                "STYwMGDDw8OzChiDILBcLpd+/ZCHPMRuueUWK5VKRpHN7rn33ntt9erVfZUAoLcIAABAH+q1BMCnP/1p"
                "GxkZIRhZYkkhMqmRCDjnnHPsRS96kW3cuNHWrFljq1evtuHhYTvssMPs2GOPtS9/+ct2xx13jDsmFIrr"
                "vLGxMRsbG7NKpWJbt261V73qVTY4ODjl9TTVEIADDzzQ3vGOd9j27dvTY8g113mt19Dvfve7WQ3j6GYC"
                "YP369SQAAAAA+tlCEwALXZJu5ZLsec97Hg+UwBz98pe/tOOPP942bNiQ9tZoHVOull4chxxyiH3mM5+x"
                "bdu2Uem/B1177bW2bt26dBjOYt9vF5pAWL9+fTo8i/MHwErmur0BADBfW7ZssY0bN2psbExxHM/4+84t"
                "/i3PzLT//vvrN7/5jfbYYw/uqcAslUol894rk8loZGRE//M//6Nf/epXuummm1QqlfSwhz1M2WxWT3/6"
                "03XEEUfogAMO4Prqcb/85S/tSU96kqIoktnSxthzff8NGzbo9ttv19DQkKtUKpbL5TifAAAA+km3ewBI"
                "ssHBQbv++utpTQLmqVQqpRX8y+Vy2rpfLpfNzMYNqSmVSlYqlbjeelAyNOc///M/O9ILQHPsAbBhw4a0"
                "B0DrMCIAAAD0iSQBkEwLN9Oy2A+gYRjaF77wBTMz44ESmJ9KpZImAFr/XiwW0+tqbGyM66uPfOxjH0un"
                "a+yVBMCee+5JAgAAAKCf7dy50/bee28LwzCdWmy6ZaEPnMm0c1Kj6vzTn/50MzPmHweANh/84AfT3llL"
                "XQ9gNsuGDRssSSpRAwAAAKAPlUolO+aYYywIAlu9evWSJwAGBgbS4P/AAw+0bdu2EfwDwBTe+973dj3w"
                "T5a9996bwB8AJPlubwAALMTBBx8s77127ty55OsqFotyzikIAl188cUaHBxUFEWSqCoNAO0+9rGPuZe9"
                "7GXKZDLd3hQ96EEPWvLChADQD0gAAOhbhULBPf5xj1ccxwqCYMnX572X914f//jH9ehHP1r1el2FQsFJ"
                "EhWlAWC3pHfUhRde6J7//OcvySwsc3HQgw9SHMckawEAAPrZ1q1bbe+997ZCoTBjYai5dhlNigs652xw"
                "cNCcc3bsscfayMhIWkwKADCzl7/85VYoFDpWFyCXy1k+n0/v42eddVY6owRDtwAAAPrYhz/8YVu7du2i"
                "JwCS13jvzXtvRx99tI2NjdnIyAgPjwAwByMjI3bEEUeYpHHJ1aVaJFkul7MwDC0IArv33nu5bwMAACwH"
                "W7ZsWbIEQDabtVwuZwcccIBt2bJl3Hzk3fisANCPqtWqbd261Z72tKelM6p0KgFw9NFHWxRF1jrNJAAA"
                "APpQMp/z5z73uUVPACRTC+655572q1/9ylrXmXQlBQDMLLlXb9u2zR796Ed3ZChAMuTgW9/6liXrb90W"
                "AAAA9LGPfvSjFgSB5XK5cV34wzCcVUJAUvq7SRfVdevW2U033WS0+APAwlWrVSuVSrb//vsvaU+AbDZr"
                "2WzW/uIv/sII+AEAAJahcrlsX/ziF9MAPxm7r1n2CAjDMH0glWQPechD7Oabb+bBEQAW2R/+8Ac74IAD"
                "0vvuUiQBhoeH7bbbbuMeDgAAsBwlYzv/7//+zw499FDL5XLjCvlphgRAEARWKBQsl8vZq171Krvvvvt4"
                "cASAJXLXXXfZwQcfbEEQLEnwf9lll3EPBwAAWAl27NhhX/rSl+zggw+edQ+AXC5nL33JS+2qq66y7du3"
                "pw+OjPcHgKUxOjpqxx9//KInAL72ta9x3wYAAFhpduzYYRdccIG96EUvskc84hG2Zs0a895bLpdL6wU8"
                "9KEPtQ996EM8LAJAl5x55pkWhmHaYyuZvs97P65Oy1RLGIbmvbfBwUE755xzuJ8DAACsNEmxKTOz0dHR"
                "9IHw/vvvt9tvv93uvfde27p1q5XLZatUKjwwAkAX/fSnP7UNGzakRfxyuZzl83nL5XKWy+XSwn7J35ME"
                "QRAEls1m7RGPeITddNNNtnPnTu7nAAAAK1G1WrVyuZwu7T8vFotmZiQAAKCLRkZGTGokaF/1qlfZ+vXr"
                "06KsSet+65LP59OhXIODg/bpT3/axsbGuI8DwAxctzcAAJZKpVKxXC437X2uWCya9175fJ77IQD0gJGR"
                "ERsbG9O3v/1tnX/++brxxhsVx/G431m1apUOPfRQHXvssXr+85+vvffem3s4AMwCN0sAAAD0tKSHlK7K"
                "tgAABXJJREFUQCKbzZK4BQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD8//bgkAAAAABA0P/XRk8A"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                "AAAAAAAAAAAAAAAAAAAAAAAALFu0UVH8oZAUAAAAAElFTkSuQmCC"
            )
            
            ghost_bytes = base64.b64decode("".join(ghost_data))
            ghost_img = Image.open(io.BytesIO(ghost_bytes))
            ghost_img = ghost_img.resize((75, 75), Image.LANCZOS)
            ghost_photo = ImageTk.PhotoImage(ghost_img)
            
            icon_label = tk.Label(header_inner, image=ghost_photo, bg=self.orange, borderwidth=0, highlightthickness=0)
            icon_label.image = ghost_photo  # Keep reference
            icon_label.pack(side=tk.LEFT, padx=(0, 12))
        except Exception as e:
            # Fallback to emoji if image fails to load
            tk.Label(header_inner, text="👻", font=("Segoe UI", 36), bg=self.orange).pack(side=tk.LEFT, padx=(0, 12))
        
        title_frame = tk.Frame(header_inner, bg=self.orange)
        title_frame.pack(side=tk.LEFT)
        tk.Label(title_frame, text="Memory Manager", font=("Segoe UI", 22, "bold"), bg=self.orange, fg="white").pack(anchor='w')
        tk.Label(title_frame, text="Download and organize all your memories", font=("Segoe UI", 9), bg=self.orange, fg="#FFE5E0").pack(anchor='w')
        
        # Content area
        self.content_area = tk.Frame(content, bg=self.white)
        self.content_area.pack(fill=tk.BOTH, expand=True, padx=40, pady=40)
        
        self.show_upload_screen()
    
    def clear_content(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()
    
    def show_upload_screen(self):
        self.clear_content()
        
        # Upload card
        upload_card = tk.Frame(self.content_area, bg="#FFF8F0", highlightbackground=self.orange, highlightthickness=3)
        upload_card.pack(pady=(0, 30))
        
        inner = tk.Frame(upload_card, bg="#FFF8F0")
        inner.pack(padx=80, pady=60)
        
        tk.Label(inner, text="📁", font=("Segoe UI", 50), bg="#FFF8F0").pack()
        tk.Label(inner, text="Select Your Snap Data", font=("Segoe UI", 18, "bold"), bg="#FFF8F0", fg=self.dark).pack(pady=(15, 8))
        tk.Label(inner, text="Choose your 'mydata' folder from Snap export", font=("Segoe UI", 10), bg="#FFF8F0", fg=self.light).pack(pady=(0, 20))
        tk.Button(inner, text="🗂️  Browse Folder", font=("Segoe UI", 12, "bold"), bg=self.orange, fg="white", relief=tk.FLAT, padx=35, pady=12, cursor="hand2", command=self.select_file).pack()
        
        # Info cards
        info_frame = tk.Frame(self.content_area, bg=self.white)
        info_frame.pack(fill=tk.X)
        
        tips = [
            ("⚡", "Fast Downloads", "5x faster with\nconcurrent downloads"),
            ("🔒", "Secure & Private", "All processing\nhappens locally"),
            ("📅", "Auto-Organized", "Named by date\nand time")
        ]
        
        for icon, title, desc in tips:
            card = tk.Frame(info_frame, bg="#F7FAFC", highlightbackground="#E2E8F0", highlightthickness=1)
            card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
            
            card_inner = tk.Frame(card, bg="#F7FAFC")
            card_inner.pack(pady=25, padx=20)
            
            tk.Label(card_inner, text=icon, font=("Segoe UI", 28), bg="#F7FAFC").pack()
            tk.Label(card_inner, text=title, font=("Segoe UI", 11, "bold"), bg="#F7FAFC", fg=self.dark).pack(pady=(12, 6))
            tk.Label(card_inner, text=desc, font=("Segoe UI", 9), bg="#F7FAFC", fg=self.light, justify=tk.CENTER).pack()
    
    def show_ready_screen(self):
        self.clear_content()
        
        tk.Label(self.content_area, text="✓", font=("Segoe UI", 50), bg=self.white, fg=self.green).pack(pady=(0, 10))
        tk.Label(self.content_area, text="Ready to Download!", font=("Segoe UI", 20, "bold"), bg=self.white, fg=self.dark).pack(pady=(0, 30))
        
        # Stats
        stats = tk.Frame(self.content_area, bg=self.white)
        stats.pack(pady=(0, 30))
        
        images = sum(1 for m in self.memories if m[1].lower() == 'image')
        videos = len(self.memories) - images
        
        for value, label, color in [(len(self.memories), "Total", self.orange), (images, "Images", self.blue), (videos, "Videos", "#F56565")]:
            card = tk.Frame(stats, bg=self.white, highlightbackground=color, highlightthickness=2, width=160, height=110)
            card.pack(side=tk.LEFT, padx=12)
            card.pack_propagate(False)
            
            inner = tk.Frame(card, bg=self.white)
            inner.place(relx=0.5, rely=0.5, anchor='center')
            
            tk.Label(inner, text=str(value), font=("Segoe UI", 32, "bold"), bg=self.white, fg=color).pack()
            tk.Label(inner, text=label, font=("Segoe UI", 10), bg=self.white, fg=self.light).pack()
        
        tk.Button(self.content_area, text="⬇️  Start Download", font=("Segoe UI", 14, "bold"), bg=self.green, fg="white", relief=tk.FLAT, pady=16, cursor="hand2", command=self.start_download).pack(fill=tk.X, pady=(0, 12))
        tk.Label(self.content_area, text="Files will be downloaded with overlays merged automatically", font=("Segoe UI", 9), bg=self.white, fg=self.light).pack()
    
    def show_downloading_screen(self):
        self.clear_content()
        
        # Header
        header = tk.Frame(self.content_area, bg=self.white)
        header.pack(fill=tk.X, pady=(0, 25))
        
        left = tk.Frame(header, bg=self.white)
        left.pack(side=tk.LEFT)
        
        self.status_icon = tk.Label(left, text="⬇️", font=("Segoe UI", 28), bg=self.white)
        self.status_icon.pack(side=tk.LEFT, padx=(0, 12))
        
        text_frame = tk.Frame(left, bg=self.white)
        text_frame.pack(side=tk.LEFT)
        
        self.status_title = tk.Label(text_frame, text="Downloading Memories", font=("Segoe UI", 16, "bold"), bg=self.white, fg=self.dark)
        self.status_title.pack(anchor='w')
        
        self.status_sub = tk.Label(text_frame, text="0 of 0 completed", font=("Segoe UI", 10), bg=self.white, fg=self.light)
        self.status_sub.pack(anchor='w')
        
        self.pause_btn = tk.Button(header, text="⏸️  Pause", font=("Segoe UI", 10, "bold"), bg=self.orange, fg="white", relief=tk.FLAT, padx=22, pady=9, cursor="hand2", command=self.toggle_pause)
        self.pause_btn.pack(side=tk.RIGHT)
        
        # Progress
        progress_frame = tk.Frame(self.content_area, bg=self.white)
        progress_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.progress_text = tk.Label(progress_frame, text="0%", font=("Segoe UI", 20, "bold"), bg=self.white, fg=self.orange)
        self.progress_text.pack(pady=(0, 8))
        
        self.progress_bg = tk.Frame(progress_frame, bg="#E2E8F0", height=16)
        self.progress_bg.pack(fill=tk.X)
        
        self.progress_fill = tk.Frame(self.progress_bg, bg=self.green, height=16)
        self.progress_fill.place(x=0, y=0, relheight=1, width=0)
        
        # Stats
        stats_frame = tk.Frame(self.content_area, bg=self.white)
        stats_frame.pack(fill=tk.X)
        
        for label, color, attr in [("Downloaded", self.green, "dl_count"), ("Failed", "#F56565", "fail_count")]:
            card = tk.Frame(stats_frame, bg=self.white, highlightbackground=color, highlightthickness=2, height=90)
            card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
            card.pack_propagate(False)
            
            inner = tk.Frame(card, bg=self.white)
            inner.place(relx=0.5, rely=0.5, anchor='center')
            
            setattr(self, attr, tk.Label(inner, text="0", font=("Segoe UI", 28, "bold"), bg=self.white, fg=color))
            getattr(self, attr).pack()
            tk.Label(inner, text=label, font=("Segoe UI", 9), bg=self.white, fg=self.light).pack()
    
    def show_complete_screen(self):
        self.clear_content()
        
        tk.Label(self.content_area, text="🎉", font=("Segoe UI", 55), bg=self.white).pack(pady=(0, 12))
        tk.Label(self.content_area, text="Download Complete!", font=("Segoe UI", 20, "bold"), bg=self.white, fg=self.dark).pack(pady=(0, 25))
        
        # Stats
        stats = tk.Frame(self.content_area, bg=self.white)
        stats.pack(pady=(0, 20))
        
        for label, value, color in [("Downloaded", self.stats['processed'], self.green), ("Failed", self.stats['failed'], "#F56565"), ("Total", len(self.memories), self.blue)]:
            card = tk.Frame(stats, bg=self.white, highlightbackground=color, highlightthickness=2, width=140, height=90)
            card.pack(side=tk.LEFT, padx=8)
            card.pack_propagate(False)
            
            inner = tk.Frame(card, bg=self.white)
            inner.place(relx=0.5, rely=0.5, anchor='center')
            
            tk.Label(inner, text=str(value), font=("Segoe UI", 24, "bold"), bg=self.white, fg=color).pack()
            tk.Label(inner, text=label, font=("Segoe UI", 9), bg=self.white, fg=self.light).pack()
        
        tk.Label(self.content_area, text=f"📁 Files saved to: {self.output_dir}", font=("Segoe UI", 9), bg=self.white, fg=self.light, wraplength=700).pack(pady=(0, 20))
        
        if self.stats['failed'] > 0 and self.failed_memories:
            tk.Button(self.content_area, text=f"🔄  Retry {len(self.failed_memories)} Failed", font=("Segoe UI", 12, "bold"), bg="#F56565", fg="white", relief=tk.FLAT, pady=13, cursor="hand2", command=self.retry_failed).pack(fill=tk.X, pady=(0, 10))
        
        tk.Button(self.content_area, text="✓  Done", font=("Segoe UI", 12, "bold"), bg=self.light, fg="white", relief=tk.FLAT, pady=13, cursor="hand2", command=self.reset).pack(fill=tk.X)
        
        # Subtle donation link
        donation_frame = tk.Frame(self.content_area, bg=self.white)
        donation_frame.pack(pady=(20, 0))
        
        donation_label = tk.Label(donation_frame, text="Enjoyed this tool? ", font=("Segoe UI", 8), bg=self.white, fg=self.light)
        donation_label.pack(side=tk.LEFT)
        
        donation_link = tk.Label(donation_frame, text="Buy me a coffee ☕", font=("Segoe UI", 8), bg=self.white, fg="#FF6B35", cursor="hand2")
        donation_link.pack(side=tk.LEFT)
        donation_link.bind("<Button-1>", lambda e: self.open_donation_link())
        
    def open_donation_link(self):
        import webbrowser
        webbrowser.open("https://buymeacoffee.com/ethanshoforost")
    
    def select_file(self):
        folder = filedialog.askdirectory(title="Select MyData Folder")
        if not folder: return
        
        html_file = os.path.join(folder, "memories_history.html")
        if not os.path.exists(html_file):
            for root, dirs, files in os.walk(folder):
                if "memories_history.html" in files:
                    html_file = os.path.join(root, "memories_history.html")
                    break
            else:
                messagebox.showerror("File Not Found", "Could not find memories_history.html")
                return
        
        self.html_file = html_file
        output_folder = filedialog.askdirectory(title="Select Output Folder")
        if output_folder:
            self.output_dir = os.path.join(output_folder, "snap_memories")
            self.process_html()
    
    def process_html(self):
        try:
            with open(self.html_file, 'r', encoding='utf-8') as f:
                html = f.read()
            
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('tbody > tr:not(:first-child)')
            
            self.memories = []
            for row in rows:
                cells = row.find_all('td')
                if len(cells) > 3:
                    link = cells[3].find('a')
                    if link and link.has_attr('onclick'):
                        onclick = link['onclick']
                        if len(onclick) >= 271:
                            self.memories.append((cells[0].get_text(strip=True), cells[1].get_text(strip=True), onclick[18:271]))
            
            if not self.memories:
                messagebox.showerror("Error", "No memories found")
                return
            
            self.show_ready_screen()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse: {str(e)}")
    
    def start_download(self):
        self.show_downloading_screen()
        threading.Thread(target=self.download_all, daemon=True).start()
    
    def download_all(self):
        self.is_downloading = True
        self.stats = {'processed': 0, 'failed': 0}
        self.failed_memories = []
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        total = len(self.memories)
        completed = 0
        lock = threading.Lock()
        
        def download_single(index_date_type_url):
            i, date, media_type, url = index_date_type_url
            while self.paused: __import__('time').sleep(0.1)
            if not self.is_downloading: return False
            
            try:
                content = requests.get(url, timeout=60).content
                # Convert UTC date to local timezone
                safe_date = convert_utc_to_local(date)
                is_zip = content[:2] == b'PK'
                
                if is_zip:
                    temp = os.path.join(self.output_dir, f"temp_{i}")
                    Path(temp).mkdir(exist_ok=True)
                    with zipfile.ZipFile(io.BytesIO(content)) as z: z.extractall(temp)
                    
                    media = overlay = None
                    is_vid = False
                    for f in os.listdir(temp):
                        fp = os.path.join(temp, f)
                        if f.lower().endswith(('.jpg', '.jpeg')): media = fp
                        elif f.lower().endswith(('.mp4', '.mov')): media, is_vid = fp, True
                        elif f.lower().endswith('.png'): overlay = fp
                    
                    if media:
                        out = os.path.join(self.output_dir, f"{safe_date}.{'mp4' if is_vid else 'jpg'}")
                        if overlay:
                            (merge_overlay_with_video if is_vid else merge_overlay_with_image)(media, overlay, out)
                        else:
                            shutil.copy(media, out)
                        with lock: self.stats['processed'] += 1
                    shutil.rmtree(temp, ignore_errors=True)
                else:
                    with open(os.path.join(self.output_dir, f"{safe_date}.{'mp4' if media_type.lower()=='video' else 'jpg'}"), 'wb') as f:
                        f.write(content)
                    with lock: self.stats['processed'] += 1
                return True
            except:
                with lock:
                    self.stats['failed'] += 1
                    self.failed_memories.append((date, media_type, url))
                return False
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(download_single, (i, d, t, u)): i for i, (d, t, u) in enumerate(self.memories)}
            for future in as_completed(futures):
                completed += 1
                ratio = completed / total
                width = int(self.progress_bg.winfo_width() * ratio)
                self.root.after(0, self.update_progress, completed, width, ratio)
        
        self.root.after(0, self.show_complete_screen)
    
    def update_progress(self, current, width, ratio):
        self.progress_fill.place(width=width)
        self.progress_text.config(text=f"{int(ratio*100)}%")
        self.dl_count.config(text=str(self.stats['processed']))
        self.fail_count.config(text=str(self.stats['failed']))
        self.status_sub.config(text=f"{current} of {len(self.memories)} completed")
    
    def toggle_pause(self):
        self.paused = not self.paused
        self.status_icon.config(text="⏸️" if self.paused else "⬇️")
        self.status_title.config(text="Paused" if self.paused else "Downloading Memories")
        self.pause_btn.config(text="▶️  Resume" if self.paused else "⏸️  Pause")
    
    def retry_failed(self):
        if not self.failed_memories: return
        self.memories = self.failed_memories.copy()
        self.show_downloading_screen()
        threading.Thread(target=self.download_all, daemon=True).start()
    
    def reset(self):
        self.html_file = self.output_dir = None
        self.memories = self.failed_memories = []
        self.stats = {'processed': 0, 'failed': 0}
        self.show_upload_screen()


root = tk.Tk()
app = SnapDownloader(root)
root.mainloop()
