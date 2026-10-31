"""Isolated inductive content analysis of saved formal-v2 positive disclosures."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ai_restrictions.governance_content import main
if __name__ == '__main__':
    main()
