import sys
from pathlib import Path

api_dir = str(Path(__file__).parent / "api")
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

from api.index import app
