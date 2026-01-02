"""AION POC - Advanced RAG System for Charging Station Documentation."""

__version__ = "0.1.0"
__author__ = "Chayan Mazumder"

# Public helpers
from .config.settings import AppSettings, get_settings
from .shared.pipeline import DemoQueryResult, build_demo_index, run_demo_query

__all__ = [
	"AppSettings",
	"DemoQueryResult",
	"build_demo_index",
	"get_settings",
	"run_demo_query",
]