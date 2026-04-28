"""
Compatibility wrapper for the collaborative pipeline step.

The active implementation now lives in Movie_Collaborative_Reco_BBA_PL4C.py.
This file remains so older docs or commands still work.
"""

from Movie_Collaborative_Reco_BBA_PL4C import *  # noqa: F401,F403
from Movie_Collaborative_Reco_BBA_PL4C import main


if __name__ == "__main__":
    main()
