import sys
from pathlib import Path

# Permite importar tests.amostras e o pacote sem instalação.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
