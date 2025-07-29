# bring_parser/parser.py
"""
Core Bring file format parser implementation.
"""

from dataclasses import dataclass
from typing import Union, List, Dict, Optional
from pathlib import Path

from .exceptions import BringParseError


@dataclass
class BringValue:
    """Base class for all Bring values."""
    pass


@dataclass  
class BringPrimitive(BringValue):
    """Represents primitive values."""
    value: Union[str, int, float, bool, None]


@dataclass
class BringObject(BringValue):
    """Represents object/dictionary values."""
    items: Dict[str, BringValue]


@dataclass
class BringArray(BringValue):
    """Represents array/list values."""
    items: List[BringValue]


@dataclass
class BringAttribute:
    """Represents a metadata attribute."""
    name: str
    value: Union[str, int, float, bool]


@dataclass
class BringKeyValuePair:
    """Represents a key-value pair with optional attributes."""
    key: str
    value: BringValue
    attributes: List[BringAttribute]


@dataclass
class BringSchemaRule:
    """Represents a rule in a schema definition.""" 
    key: str
    type: str
    attributes: List[BringAttribute]


@dataclass
class BringSchema:
    """Represents a schema definition."""
    name: str
    rules: List[BringSchemaRule]


class BringParser:
    """Main parser for Bring file format."""

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.col = 1

    def parse(self) -> Dict[str, Union[BringValue, BringSchema]]:
        """Parse the Bring content."""
        try:
            result = {}
            while not self.is_eof():
                self.skip_whitespace()
                if self.is_eof():
                    break
                
                if self.peek() == '#':
                    self.skip_comment()
                    continue
                
                if self.match('schema'):
                    self.skip_whitespace()
                    schema = self.parse_schema()
                    result[f"schema:{schema.name}"] = schema
                    continue
                
                kv_pair = self.parse_key_value_pair()
                result[kv_pair.key] = kv_pair.value
            
            return result
        except Exception as e:
            if isinstance(e, BringParseError):
                raise
            raise BringParseError(f"Parse error: {str(e)} at line {self.line}, column {self.col}")

    def parse_key_value_pair(self) -> BringKeyValuePair:
        """Parse a key-value pair with optional attributes."""
        key = self.parse_key()
        self.skip_whitespace()
        
        attributes = []
        while self.peek() == '@':
            self.advance()
            attr_name = self.parse_identifier()
            self.skip_whitespace()
            self.expect('=')
            self.skip_whitespace()
            attr_value = self.parse_primitive_value()
            attributes.append(BringAttribute(attr_name, attr_value))
            self.skip_whitespace()
        
        self.expect('=')
        self.skip_whitespace()
        value = self.parse_value()
        
        return BringKeyValuePair(key=key, value=value, attributes=attributes)

    def parse_value(self) -> BringValue:
        """Parse any value type."""
        char = self.peek()
        if char == '{':
            return self.parse_object()
        elif char == '[':
            return self.parse_array()
        elif char in ('"', "'"):
            return BringPrimitive(self.parse_string())
        elif char.isdigit() or char == '-':
            return BringPrimitive(self.parse_number())
        elif self.match('true'):
            return BringPrimitive(True)
        elif self.match('false'):
            return BringPrimitive(False)
        elif self.match('null'):
            return BringPrimitive(None)
        else:
            raise self.error(f"Unexpected character: {char}")

    def parse_object(self) -> BringObject:
        """Parse an object."""
        self.expect('{')
        self.skip_whitespace()
        
        items = {}
        while not self.is_eof() and self.peek() != '}':
            if self.peek() == '#':
                self.skip_comment()
                self.skip_whitespace()
                continue
            
            kv_pair = self.parse_key_value_pair()
            items[kv_pair.key] = kv_pair.value
            
            self.skip_whitespace()
            if self.peek() == ',':
                self.advance()
                self.skip_whitespace()
        
        self.expect('}')
        return BringObject(items)

    def parse_array(self) -> BringArray:
        """Parse an array."""
        self.expect('[')  
        self.skip_whitespace()
        
        items = []
        while not self.is_eof() and self.peek() != ']':
            if self.peek() == '#':
                self.skip_comment()
                self.skip_whitespace()
                continue
                
            items.append(self.parse_value())
            self.skip_whitespace()
            if self.peek() == ',':
                self.advance()
                self.skip_whitespace()
        
        self.expect(']')
        return BringArray(items)

    def parse_schema(self) -> BringSchema:
        """Parse a schema definition."""
        name = self.parse_identifier()
        self.skip_whitespace()
        self.expect('{')
        self.skip_whitespace()
        
        rules = []
        while not self.is_eof() and self.peek() != '}':
            if self.peek() == '#':
                self.skip_comment()
                self.skip_whitespace()
                continue
            
            key = self.parse_key()
            self.skip_whitespace()
            self.expect('=')
            self.skip_whitespace()
            type_name = self.parse_identifier()
            self.skip_whitespace()
            
            attrs = []
            while self.peek() == '@':
                self.advance()
                attr_name = self.parse_identifier()
                self.skip_whitespace()
                self.expect('=')
                self.skip_whitespace()
                attr_value = self.parse_primitive_value()
                attrs.append(BringAttribute(attr_name, attr_value))
                self.skip_whitespace()
            
            rules.append(BringSchemaRule(key, type_name, attrs))
            self.skip_whitespace()
        
        self.expect('}')
        return BringSchema(name, rules)

    def parse_key(self) -> str:
        """Parse a key."""
        if self.peek() in ('"', "'"):
            return self.parse_string()
        return self.parse_identifier()

    def parse_primitive_value(self) -> Union[str, int, float, bool]:
        """Parse a primitive value."""
        char = self.peek()
        if char in ('"', "'"):
            return self.parse_string()
        elif char.isdigit() or char == '-':
            return self.parse_number()
        elif self.match('true'):
            return True
        elif self.match('false'):
            return False
        else:
            raise self.error("Expected primitive value")

    def parse_string(self) -> str:
        """Parse a quoted string."""
        quote_char = self.peek()
        self.advance()
        result = []
        while not self.is_eof() and self.peek() != quote_char:
            if self.peek() == '\\':
                self.advance()
                if self.is_eof():
                    raise self.error("Unterminated string")
                escape_char = self.advance()
                if escape_char == 'n':
                    result.append('\n')
                elif escape_char == 't':
                    result.append('\t')
                elif escape_char == 'r':
                    result.append('\r')
                elif escape_char == '\\':
                    result.append('\\')
                elif escape_char == quote_char:
                    result.append(quote_char)
                else:
                    result.append(escape_char)
            else:
                result.append(self.advance())
        
        if self.is_eof():
            raise self.error("Unterminated string")
        self.advance()
        return ''.join(result)

    def parse_number(self) -> Union[int, float]:
        """Parse integer or float."""
        start_pos = self.pos
        is_float = False
        
        if self.peek() == '-':
            self.advance()
        
        if not self.peek().isdigit():
            raise self.error("Expected digit")
        
        while not self.is_eof() and self.peek().isdigit():
            self.advance()
        
        if not self.is_eof() and self.peek() == '.':
            is_float = True
            self.advance()
            if not self.peek().isdigit():
                raise self.error("Expected digit after decimal")
            while not self.is_eof() and self.peek().isdigit():
                self.advance()
        
        num_str = self.text[start_pos:self.pos]
        try:
            return float(num_str) if is_float else int(num_str)
        except ValueError:
            raise self.error(f"Invalid number: {num_str}")

    def parse_identifier(self) -> str:
        """Parse an identifier."""
        if not (self.peek().isalpha() or self.peek() == '_'):
            raise self.error(f"Expected identifier, got '{self.peek()}'")
        
        result = [self.advance()]
        while not self.is_eof() and (self.peek().isalnum() or self.peek() == '_'):
            result.append(self.advance())
        
        return ''.join(result)

    def skip_whitespace(self):
        """Skip whitespace."""
        while not self.is_eof() and self.peek().isspace():
            if self.peek() == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            self.advance()

    def skip_comment(self):
        """Skip a comment line."""
        self.expect('#')
        while not self.is_eof() and self.peek() != '\n':
            self.advance()

    def match(self, s: str) -> bool:
        """Check if current position matches string."""
        if self.text.startswith(s, self.pos):
            for _ in s:
                self.advance()
            return True
        return False

    def expect(self, s: str):
        """Expect a specific string."""
        if not self.match(s):
            raise self.error(f"Expected '{s}'")

    def peek(self) -> str:
        """Peek at current character."""
        return self.text[self.pos] if self.pos < len(self.text) else ''

    def advance(self) -> str:
        """Advance to next character."""
        if self.is_eof():
            return ''
        
        char = self.text[self.pos]
        self.pos += 1
        if char == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return char

    def is_eof(self) -> bool:
        """Check if at end of input."""
        return self.pos >= len(self.text)

    def error(self, message: str) -> BringParseError:
        """Create parse error with position."""
        return BringParseError(f"{message} at line {self.line}, column {self.col}")


def parse_bring_file(file_path: Union[str, Path]) -> Dict[str, Union[BringValue, BringSchema]]:
    """Parse a Bring file from disk."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Bring file not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return parse_bring_string(content)
    except UnicodeDecodeError as e:
        raise BringParseError(f"File encoding error: {e}")


def parse_bring_string(content: str) -> Dict[str, Union[BringValue, BringSchema]]:
    """Parse a Bring format string."""
    parser = BringParser(content)
    return parser.parse()
