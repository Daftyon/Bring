# bring_parser/__init__.py
"""
Bring File Format Parser

A modern, human-readable configuration and package management format parser.
"""

__version__ = "1.0.0"
__author__ = "Daftyon Team"
__email__ = "contact@daftyon.com"
__description__ = "Parser for the Bring file format - modern configuration and package management"

# Import core classes and functions
from .parser import (
    BringParser,
    BringValue, 
    BringPrimitive,
    BringObject,
    BringArray,
    BringAttribute,
    BringKeyValuePair,
    BringSchemaRule,
    BringSchema,
    parse_bring_file,
    parse_bring_string
)

from .exceptions import (
    BringParseError,
    BringSchemaError,
    BringSyntaxError
)

try:
    from .validator import BringValidator
except ImportError:
    # Fallback if validator not available
    class BringValidator:
        def __init__(self):
            pass
        def add_schema(self, schema):
            pass
        def validate_object(self, obj, schema_name):
            return []

try:
    from .utils import to_dict, to_json, from_dict
except ImportError:
    # Simple fallback implementations
    def to_dict(bring_value):
        """Simple fallback to_dict implementation."""
        if hasattr(bring_value, 'items'):
            if isinstance(bring_value.items, dict):
                return {k: to_dict(v) for k, v in bring_value.items.items()}
            elif isinstance(bring_value.items, list):
                return [to_dict(item) for item in bring_value.items]
        elif hasattr(bring_value, 'value'):
            return bring_value.value
        elif isinstance(bring_value, dict):
            result = {}
            for key, value in bring_value.items():
                if not key.startswith('schema:'):
                    result[key] = to_dict(value)
            return result
        return bring_value
    
    def to_json(bring_value, indent=2):
        """Simple fallback to_json implementation."""
        import json
        return json.dumps(to_dict(bring_value), indent=indent)
    
    def from_dict(data):
        """Simple fallback from_dict implementation."""
        return data

__all__ = [
    # Core classes
    'BringParser',
    'BringValue',
    'BringPrimitive', 
    'BringObject',
    'BringArray',
    'BringAttribute',
    'BringKeyValuePair',
    'BringSchemaRule',
    'BringSchema',
    
    # Utility functions
    'parse_bring_file',
    'parse_bring_string',
    'to_dict',
    'to_json', 
    'from_dict',
    
    # Validation
    'BringValidator',
    
    # Exceptions
    'BringParseError',
    'BringSchemaError',
    'BringSyntaxError'
]
