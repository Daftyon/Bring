# tests/test_parser.py
import os
import sys
import unittest
from pathlib import Path

# Add parent directory to path for importing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bring_parser.parser import parse_bring_file, BringPrimitive, BringObject, BringArray
from bring_parser.exceptions import BringParseError

data = parse_bring_file("hello.bring")
print(data)  # 3000
