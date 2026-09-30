import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from virus_cleaner import ensure_admin
from main_window import run

if __name__ == "__main__":
    ensure_admin()  # degilse UAC ile kendini yukseltip eski sureci kapatir
    run()
