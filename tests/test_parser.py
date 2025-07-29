# tests/test_parser.py
import os
import sys
import unittest
from pathlib import Path

# Add parent directory to path for importing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bring_parser.parser import parse_bring_file, BringPrimitive, BringObject, BringArray
from bring_parser.exceptions import BringParseError

class TestBringParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Create a test file before running tests"""
        cls.test_file = Path("testfile.bring")
        cls.test_content = """
        # Example configuration file
        app = {
            name = "MyApp" @version="1.0"
            port = 8080 @min=1024 @max=65535
            debug = false
            database = {
                url = "postgres://user:pass@localhost:5432/db"
                timeout = 30 @unit="seconds"
            }
        }

        schema User {
            id = number @min=1
            name = string @maxLength=50
            email = string @format="email"
        }

        users = [
            { id = 1, name = "Alice", email = "alice@example.com" }
            { id = 2, name = "Bob", email = "bob@example.com" }
        ]
        """
        cls.test_file.write_text(cls.test_content)

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests"""
        cls.test_file.unlink()

    def test_file_parsing(self):
        """Test parsing from file"""
        result = parse_bring_file("file.bring")
        
        # Test app config
        self.assertIsInstance(result['app'], BringObject)
        self.assertEqual(result['app'].items['name'].value, "MyApp")
        self.assertEqual(result['app'].items['port'].value, 8080)
        self.assertEqual(result['app'].items['debug'].value, False)
        
        # Test nested database config
        db = result['app'].items['database']
        self.assertIsInstance(db, BringObject)
        self.assertEqual(db.items['url'].value, "postgres://user:pass@localhost:5432/db")
        
        # Test schema
        self.assertIn("schema:User", result)
        schema = result["schema:User"]
        self.assertEqual(len(schema.rules), 3)
        
        # Test users array
        self.assertIsInstance(result['users'], BringArray)
        self.assertEqual(len(result['users'].items), 2)
        self.assertEqual(result['users'].items[0].items['name'].value, "Alice")

    def test_attributes(self):
        """Test attribute parsing"""
        result = parse_bring_file("file.bring")
        
        # Check port attributes
        port = result['app'].items['port']
        self.assertEqual(len(port.attributes), 2)
        self.assertEqual(port.attributes[0].name, "min")
        self.assertEqual(port.attributes[0].value, 1024)
        
        # Check schema rule attributes
        schema = result["schema:User"]
        id_rule = next(r for r in schema.rules if r.key == "id")
        self.assertEqual(id_rule.attributes[0].name, "min")
        self.assertEqual(id_rule.attributes[0].value, 1)

if __name__ == "__main__":
    unittest.main()
