import sys
from pathlib import Path

# Make the scripts/ folder importable from tests
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
