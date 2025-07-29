# bring_parser/exceptions.py
"""
Exception classes for the Bring parser.
"""


class BringParseError(Exception):
    """Base exception for Bring parsing errors."""
    pass


class BringSyntaxError(BringParseError):
    """Exception raised for syntax errors in Bring files."""
    pass


class BringSchemaError(BringParseError):
    """Exception raised for schema validation errors."""
    pass
