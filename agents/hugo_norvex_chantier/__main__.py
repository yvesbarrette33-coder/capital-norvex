"""Entry point pour `python -m agents.hugo_norvex_chantier`."""
from .orchestrator import main
import sys

if __name__ == "__main__":
    sys.exit(main())
