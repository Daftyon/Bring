import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Union, List, Dict, Optional

# ====================== Data Structures ======================

@dataclass
class BringValue:
    pass

@dataclass
class BringPrimitive(BringValue):
    value: Union[str, int, float, bool, None]

@dataclass
class BringObject(BringValue):
    items: Dict[str, BringValue]

@dataclass
class BringArray(BringValue):
    items: List[BringValue]

@dataclass
class BringAttribute:
    name: str
    value: Union[str, int, float, bool]

@dataclass
class BringKeyValuePair:
    key: str
    value: BringValue
    attributes: List[BringAttribute]

@dataclass
class BringSchemaRule:
    key: str
    type: str
    attributes: List[BringAttribute]

@dataclass
class BringSchema:
    name: str
    rules: List[BringSchemaRule]

# ====================== Parser Implementation ======================

class BringParser:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.col = 1

    def parse(self) -> Dict[str, Union[BringValue, BringSchema]]:
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

    def parse_key_value_pair(self) -> BringKeyValuePair:
        key = self.parse_key()
        self.skip_whitespace()
        
        attributes = []
        while self.peek() == '@':
            self.advance()  # Skip @
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
        self.expect('[')
        self.skip_whitespace()
        
        items = []
        while not self.is_eof() and self.peek() != ']':
            items.append(self.parse_value())
            self.skip_whitespace()
            if self.peek() == ',':
                self.advance()
                self.skip_whitespace()
        
        self.expect(']')
        return BringArray(items)

    def parse_schema(self) -> BringSchema:
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
        if self.peek() in ('"', "'"):
            return self.parse_string()
        return self.parse_identifier()

    def parse_primitive_value(self) -> Union[str, int, float, bool]:
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
        quote_char = self.peek()
        self.advance()
        result = []
        while not self.is_eof() and self.peek() != quote_char:
            if self.peek() == '\\':
                self.advance()
                if self.is_eof():
                    raise self.error("Unterminated string")
                result.append(self.advance())
            else:
                result.append(self.advance())
        
        if self.is_eof():
            raise self.error("Unterminated string")
        self.advance()
        return ''.join(result)

    def parse_number(self) -> Union[int, float]:
        start_pos = self.pos
        is_float = False
        
        if self.peek() == '-':
            self.advance()
        
        while not self.is_eof() and self.peek().isdigit():
            self.advance()
        
        if not self.is_eof() and self.peek() == '.':
            is_float = True
            self.advance()
            while not self.is_eof() and self.peek().isdigit():
                self.advance()
        
        num_str = self.text[start_pos:self.pos]
        return float(num_str) if is_float else int(num_str)

    def parse_identifier(self) -> str:
        if not (self.peek().isalpha() or self.peek() == '_'):
            raise self.error(f"Expected identifier, got '{self.peek()}'")
        
        result = [self.advance()]
        while not self.is_eof() and (self.peek().isalnum() or self.peek() == '_'):
            result.append(self.advance())
        
        return ''.join(result)

    def skip_whitespace(self):
        while not self.is_eof() and self.peek().isspace():
            if self.peek() == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            self.advance()

    def skip_comment(self):
        self.expect('#')
        while not self.is_eof() and self.peek() != '\n':
            self.advance()

    def match(self, s: str) -> bool:
        if self.text.startswith(s, self.pos):
            for _ in s:
                self.advance()
            return True
        return False

    def expect(self, s: str):
        if not self.match(s):
            raise self.error(f"Expected '{s}'")

    def peek(self) -> str:
        return self.text[self.pos] if self.pos < len(self.text) else ''

    def advance(self) -> str:
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
        return self.pos >= len(self.text)

    def error(self, message: str) -> Exception:
        return SyntaxError(f"{message} at line {self.line}, column {self.col}")

# ====================== File Handling ======================

def parse_bring_file(file_path: str) -> Dict[str, Union[BringValue, BringSchema]]:
    """Parse a Bring file from disk"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        parser = BringParser(content)
        return parser.parse()
    except FileNotFoundError:
        print(f"Error: File not found - {file_path}")
        sys.exit(1)
    except SyntaxError as e:
        print(f"Parse error in {file_path}: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "test.bring"
    
    if not Path(file_path).exists():
        print(f"Error: File not found - {file_path}")
        sys.exit(1)
    
    result = parse_bring_file(file_path)
    
    # Pretty print the result
    print(f"Successfully parsed {file_path}:")
    print("=" * 50)
    
    import pprint
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(result)

if __name__ == "__main__":
    main()
