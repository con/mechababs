"""Make the `mechababs` package importable in unit tests without an editable
install, so `pytest tests/test_*.py` runs from a bare checkout.

Scoped to the whole tests/ tree; the e2e suite (tests/e2e/) doesn't import the
package (it drives the campaign venv's `mechababs` binary via subprocess), so
this only affects the pure unit tests.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
