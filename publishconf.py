import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pelicanconf import *  # noqa: F401,F403


SITEURL = "https://dalembinha.github.io"
RELATIVE_URLS = False
