# bring_parser/utils.py
"""
Utility functions for working with Bring data structures.
"""

import json
from typing import Any, Dict, Union, List
from .parser import BringValue, BringPrimitive, BringObject, BringArray, BringSchema


def to_dict(bring_value: Union[BringValue, BringSchema, Dict]) -> Any:
    """
    Convert Bring data structures to native Python dictionaries.
    
    Args:
        bring_value: Bring value to convert
        
    Returns:
        Native Python data structure
    """
    if isinstance(bring_value, dict):
        # Handle top-level parsed results
        result = {}
        for key, value in bring_value.items():
            if key.startswith('schema:'):
                # Convert schema to dict representation
                schema_name = key.replace('schema:', '')
                result[f'_schema_{schema_name}'] = schema_to_dict(value)
            else:
                result[key] = to_dict(value)
        return result
    
    elif isinstance(bring_value, BringPrimitive):
        return bring_value.value
    
    elif isinstance(bring_value, BringObject):
        return {key: to_dict(value) for key, value in bring_value.items.items()}
    
    elif isinstance(bring_value, BringArray):
        return [to_dict(item) for item in bring_value.items]
    
    elif isinstance(bring_value, BringSchema):
        return schema_to_dict(bring_value)
    
    else:
        return bring_value


def schema_to_dict(schema: BringSchema) -> Dict[str, Any]:
    """Convert a BringSchema to dictionary representation."""
    return {
        'name': schema.name,
        'rules': [
            {
                'key': rule.key,
                'type': rule.type,
                'attributes': {attr.name: attr.value for attr in rule.attributes}
            }
            for rule in schema.rules
        ]
    }


def to_json(bring_value: Union[BringValue, Dict], indent: int = 2) -> str:
    """
    Convert Bring data to JSON string.
    
    Args:
        bring_value: Bring value to convert
        indent: JSON indentation level
        
    Returns:
        JSON string representation
    """
    return json.dumps(to_dict(bring_value), indent=indent, ensure_ascii=False)


def from_dict(data: Dict[str, Any]) -> Dict[str, BringValue]:
    """
    Convert Python dictionary to Bring data structures.
    
    Args:
        data: Python dictionary to convert
        
    Returns:
        Dictionary of Bring values
    """
    result = {}
    
    for key, value in data.items():
        result[key] = _dict_to_bring_value(value)
    
    return result


def _dict_to_bring_value(value: Any) -> BringValue:
    """Convert a Python value to a BringValue."""
    if isinstance(value, dict):
        items = {k: _dict_to_bring_value(v) for k, v in value.items()}
        return BringObject(items)
    
    elif isinstance(value, list):
        items = [_dict_to_bring_value(item) for item in value]
        return BringArray(items)
    
    else:
        # Primitive value
        return BringPrimitive(value)


def extract_attributes(bring_value: BringValue) -> Dict[str, Any]:
    """
    Extract all attributes from a Bring value recursively.
    
    Args:
        bring_value: Bring value to extract from
        
    Returns:
        Dictionary of all found attributes
    """
    attributes = {}
    
    def _extract_recursive(value, path=""):
        if hasattr(value, 'attributes') and value.attributes:
            for attr in value.attributes:
                attr_path = f"{path}.{attr.name}" if path else attr.name
                attributes[attr_path] = attr.value
        
        if isinstance(value, BringObject):
            for key, item in value.items.items():
                new_path = f"{path}.{key}" if path else key
                _extract_recursive(item, new_path)
        
        elif isinstance(value, BringArray):
            for i, item in enumerate(value.items):
                new_path = f"{path}[{i}]" if path else f"[{i}]"
                _extract_recursive(item, new_path)
    
    _extract_recursive(bring_value)
    return attributes


def flatten_config(bring_data: Dict[str, BringValue], separator: str = ".") -> Dict[str, Any]:
    """
    Flatten nested Bring configuration to dot-notation keys.
    
    Args:
        bring_data: Parsed Bring data
        separator: Key separator (default: ".")
        
    Returns:
        Flattened configuration dictionary
    """
    def _flatten(obj, parent_key=""):
        items = []
        
        if isinstance(obj, BringObject):
            for key, value in obj.items.items():
                new_key = f"{parent_key}{separator}{key}" if parent_key else key
                items.extend(_flatten(value, new_key).items())
        
        elif isinstance(obj, BringArray):
            for i, value in enumerate(obj.items):
                new_key = f"{parent_key}{separator}{i}" if parent_key else str(i)
                items.extend(_flatten(value, new_key).items())
        
        elif isinstance(obj, BringPrimitive):
            return {parent_key: obj.value}
        
        else:
            return {parent_key: obj}
        
        return dict(items)
    
    result = {}
    for key, value in bring_data.items():
        if not key.startswith('schema:'):
            result.update(_flatten(value, key))
    
    return result
