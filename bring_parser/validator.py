# bring_parser/validator.py
"""
Simple schema validation for Bring configurations.
"""

from typing import Dict, List
from .parser import BringValue, BringPrimitive, BringObject, BringArray, BringSchema
from .exceptions import BringSchemaError


class BringValidator:
    """Simple validator for Bring configurations."""
    
    def __init__(self):
        self.schemas: Dict[str, BringSchema] = {}
    
    def add_schema(self, schema: BringSchema):
        """Add a schema for validation."""
        self.schemas[schema.name] = schema
    
    def validate_object(self, obj: BringObject, schema_name: str) -> List[str]:
        """Validate a BringObject against a schema."""
        if schema_name not in self.schemas:
            raise BringSchemaError(f"Schema '{schema_name}' not found")
        
        schema = self.schemas[schema_name]
        errors = []
        
        for rule in schema.rules:
            if rule.key in obj.items:
                value = obj.items[rule.key]
                # Basic type checking
                if rule.type == 'string' and not (isinstance(value, BringPrimitive) and isinstance(value.value, str)):
                    errors.append(f"Expected string for {rule.key}")
                elif rule.type == 'number' and not (isinstance(value, BringPrimitive) and isinstance(value.value, (int, float))):
                    errors.append(f"Expected number for {rule.key}")
                elif rule.type == 'boolean' and not (isinstance(value, BringPrimitive) and isinstance(value.value, bool)):
                    errors.append(f"Expected boolean for {rule.key}")
        
        return errors
