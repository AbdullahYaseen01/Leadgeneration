import sys
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.app import app

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, port=5000)
