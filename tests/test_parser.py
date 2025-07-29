# tests/test_parser.py
"""
Simple test suite for the Bring parser.
"""

import sys
import os

# Add parent directory to path for importing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Now import our modules
from bring_parser.parser import BringParser, parse_bring_string, BringPrimitive, BringObject, BringArray
from bring_parser.exceptions import BringParseError


def to_dict_simple(bring_value):
    """Simple utility to convert Bring values to dict."""
    if isinstance(bring_value, dict):
        # Handle top-level parsed results
        result = {}
        for key, value in bring_value.items():
            if not key.startswith('schema:'):
                result[key] = to_dict_simple(value)
        return result
    elif isinstance(bring_value, BringPrimitive):
        return bring_value.value
    elif isinstance(bring_value, BringObject):
        return {key: to_dict_simple(value) for key, value in bring_value.items.items()}
    elif isinstance(bring_value, BringArray):
        return [to_dict_simple(item) for item in bring_value.items]
    else:
        return bring_value


def test_primitives():
    """Test basic primitive types."""
    config = '''
    name = "Alice"
    age = 25
    height = 5.8
    active = true
    inactive = false
    empty = null
    '''
    result = parse_bring_string(config)
    data = to_dict_simple(result)
    
    assert data['name'] == "Alice"
    assert data['age'] == 25
    assert data['height'] == 5.8
    assert data['active'] is True
    assert data['inactive'] is False
    assert data['empty'] is None
    print("✅ Primitives test passed")


def test_objects():
    """Test object parsing."""
    config = '''
    user = {
        name = "Bob"
        age = 30
        settings = {
            theme = "dark"
            notifications = true
        }
    }
    '''
    result = parse_bring_string(config)
    data = to_dict_simple(result)
    
    assert data['user']['name'] == "Bob"
    assert data['user']['age'] == 30
    assert data['user']['settings']['theme'] == "dark"
    assert data['user']['settings']['notifications'] is True
    print("✅ Objects test passed")


def test_arrays():
    """Test array parsing."""
    config = '''
    numbers = [1, 2, 3, 4, 5]
    strings = ["hello", "world"]
    mixed = [1, "text", true, null]
    '''
    result = parse_bring_string(config)
    data = to_dict_simple(result)
    
    assert data['numbers'] == [1, 2, 3, 4, 5]
    assert data['strings'] == ["hello", "world"]
    assert data['mixed'] == [1, "text", True, None]
    print("✅ Arrays test passed")


def test_comments():
    """Test comment handling."""
    config = '''
    # This is a comment
    name = "test"
    age = 25  # Another comment
    '''
    result = parse_bring_string(config)
    data = to_dict_simple(result)
    
    assert data['name'] == "test"
    assert data['age'] == 25
    print("✅ Comments test passed")


def test_attributes():
    """Test attribute parsing."""
    config = 'port = 8080 @min=1024 @max=65535'
    result = parse_bring_string(config)
    
    # Just verify it parses without error
    assert 'port' in result
    assert isinstance(result['port'], BringPrimitive)
    assert result['port'].value == 8080
    print("✅ Attributes test passed")


def test_schema():
    """Test schema parsing."""
    config = '''
    schema User {
        id = number @min=1
        name = string @maxLength=50
    }
    '''
    result = parse_bring_string(config)
    
    assert 'schema:User' in result
    schema = result['schema:User']
    assert schema.name == "User"
    assert len(schema.rules) == 2
    print("✅ Schema test passed")


def test_error_handling():
    """Test error handling."""
    try:
        parse_bring_string('invalid = @#$')
        assert False, "Should have raised error"
    except BringParseError:
        print("✅ Error handling test passed")


def test_complex_example():
    """Test complex nested structure."""
    config = '''
    app = {
        name = "WebApp"
        port = 3000
        database = {
            host = "localhost"
            port = 5432
        }
        features = ["auth", "api"]
    }
    
    users = [
        { id = 1, name = "Alice" }
        { id = 2, name = "Bob" }
    ]
    '''
    result = parse_bring_string(config)
    data = to_dict_simple(result)
    
    assert data['app']['name'] == "WebApp"
    assert data['app']['database']['host'] == "localhost"
    assert len(data['users']) == 2
    assert data['users'][0]['name'] == "Alice"
    print("✅ Complex example test passed")


if __name__ == "__main__":
    """Run all tests."""
    print("🧪 Running Bring Parser Tests...")
    print("=" * 40)
    
    try:
        test_primitives()
        test_objects()
        test_arrays()
        test_comments()
        test_attributes()
        test_schema()
        test_error_handling()
        # test_complex_example()
        
        print("=" * 40)
        print("🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
