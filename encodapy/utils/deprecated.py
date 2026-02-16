"""
Description: This module provides a decorator to mark functions as deprecated.
Author: Martin Altenburger
"""
import warnings
from functools import wraps
def deprecated(message: str):
    """Decorator to mark functions as deprecated"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated. {message}",
                DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator
