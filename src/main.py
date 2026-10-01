import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main_window import run

if __name__ == "__main__":
    # Runs without admin privileges by default (UAC is requested on-demand only when needed, e.g. clean_pc)
    run()
