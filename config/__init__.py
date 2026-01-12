"""
Configuration module for Cashflow
"""
from .mongodb_config import get_mongodb_connection_string, setup_mongodb_env

__all__ = ["get_mongodb_connection_string", "setup_mongodb_env"]

