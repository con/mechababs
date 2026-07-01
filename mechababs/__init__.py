"""mechababs — automation glue for running BIDS apps across datasets via BABS.

This package is the home for the operate-side CLI (``configure`` /
``add-dataset`` / ``iterate``) and its ``state.py`` ledger accessor. The
environment half of the campaign bootstrap lives in the root ``bootstrap.sh``;
the remaining top-level scripts migrate in here over time.
"""

__version__ = "0.0.1"
