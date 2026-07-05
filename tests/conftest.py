import sys
from pathlib import Path

# Projekt-Wurzel importierbar machen (copilot-Paket), egal von wo pytest läuft.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
