"""A future-based interface to ecmwf-api-client"""

from .api import ECMWFDataServer, ECMWFService, wait, as_completed


__all__ = (
    "ECMWFDataServer",
    "ECMWFService",
    "wait",
    "as_completed"
)

__version__ = "1.1.0"

