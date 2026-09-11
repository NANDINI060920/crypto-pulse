"""
conftest.py
-----------
Ensures the project root is on sys.path so tests can do
`import storage`, `import anomaly`, `import ingest` directly,
regardless of where pytest is invoked from.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))