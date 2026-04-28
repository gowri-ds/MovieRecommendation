"""
Compatibility wrapper for the collaborative leave-one-out pipeline step.

The active implementation now lives in
Movie_Collaborative_Reco_BBA_PL4D_LeaveOneOut.py. This file remains so
older docs or commands still work.
"""

from Movie_Collaborative_Reco_BBA_PL4D_LeaveOneOut import *  # noqa: F401,F403
from Movie_Collaborative_Reco_BBA_PL4D_LeaveOneOut import main


if __name__ == "__main__":
    main()
