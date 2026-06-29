"""mechababs — automation glue for running BIDS apps across datasets via BABS.

This package is the home for the operate-side CLI (``add-dataset`` / ``iterate``)
and its ``state.py`` ledger accessor. For now it is an installable shell: the
bootstrap scripts (``init-campaign.py``, ``cluster-setup.py``) live at the repo
root, and the remaining top-level scripts migrate in here over time.
"""

__version__ = "0.0.1"
