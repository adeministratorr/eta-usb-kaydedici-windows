import os
import sys

# Windows PyInstaller ortamında QtWebEngine render process kilitlenmelerini ve GPU beyaz ekran sorununu önle
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu --disable-software-rasterizer")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main_window import run

if __name__ == "__main__":
    # Runs without admin privileges by default (UAC is requested on-demand only when needed, e.g. clean_pc)
    run()
