import sys
from pathlib import Path

# Add api directory to sys.path so it works both locally and in serverless
api_dir = str(Path(__file__).parent / "api")
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

from api.index import app
