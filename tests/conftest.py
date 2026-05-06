import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Makes `subway_equity` importable (from src/utility_functions/)
sys.path.insert(0, str(ROOT / "src"))

# Makes script files loadable by importlib in test_scripts.py
sys.path.insert(0, str(ROOT / "scripts"))
