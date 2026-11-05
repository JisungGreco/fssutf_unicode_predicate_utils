"""Public API for fssutf_unicode_predicate_utils.

Exports:
    - is_fssutf: predicate for a single Unicode scalar value
    - is_fssutf_string: predicate for a whole string
    - FSSUTFError: raised by strict validation helpers
"""

from .core import FSSUTFError, is_fssutf, is_fssutf_string

__all__ = ["FSSUTFError", "is_fssutf", "is_fssutf_string"]
