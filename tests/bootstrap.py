import os
import sys


def add_src_path() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
    if root not in sys.path:
        sys.path.insert(0, root)
