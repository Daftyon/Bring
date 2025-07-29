# bring_parser/cli.py
"""
Command line interface for the Bring parser.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

from .. import __version__
from .parser import parse_bring_file, parse_bring_string
from .utils import to_dict, to_json
from .validator import BringValidator
from .exceptions import BringParseError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Bring file format parser and validator",
        prog="bring-parser"
    )
    
    parser.add_argument(
        "file",
        nargs="?",
        help="Bring file to parse (reads from stdin if not provided)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"bring-parser {__version__}"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["dict", "json", "pretty"],
        default="pretty",
        help="Output format (default: pretty)"
    )
    
    parser.add_argument(
        "--validate", "-v",
        metavar="SCHEMA",
        help="Validate against schema name"
    )
    
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level (default: 2)"
    )
    
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show parsing statistics"
    )
    
    args = parser.parse_args()
    
    try:
        # Read input
        if args.file:
            if not Path(args.file).exists():
                print(f"Error: File not found - {args.file}", file=sys.stderr)
                sys.exit(1)
            result = parse_bring_file(args.file)
            source = args.file
        else:
            content = sys.stdin.read()
            if not content.strip():
                print("Error: No input provided", file=sys.stderr)
                sys.exit(1)
            result = parse_bring_string(content)
            source = "<stdin>"
        
        # Validation
        if args.validate:
            validator = BringValidator()
            
            # Add schemas from parsed result
            for key, value in result.items():
                if key.startswith('schema:'):
                    validator.add_schema(value)
            
            # Find data to validate
            data_items = {k: v for k, v in result.items() if not k.startswith('schema:')}
            
            if not data_items:
                print("Warning: No data found to validate", file=sys.stderr)
            else:
                errors = []
                for key, value in data_items.items():
                    if hasattr(value, 'items'):  # BringObject
                        errors.extend(validator.validate(value.items, args.validate))
                    else:
                        errors.extend(validator.validate({key: value}, args.validate))
                
                if errors:
                    print(f"Validation errors for schema '{args.validate}':", file=sys.stderr)
                    for error in errors:
                        print(f"  • {error}", file=sys.stderr)
                    sys.exit(1)
                else:
                    print(f"✅ Validation passed for schema '{args.validate}'")
        
        # Output results
        if args.format == "dict":
            print(repr(to_dict(result)))
        
        elif args.format == "json":
            print(to_json(result, indent=args.indent))
        
        else:  # pretty format
            print_pretty(result, source, args.no_color, args.stats)
    
    except BringParseError as e:
        print(f"Parse error: {e}", file=sys.stderr)
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled", file=sys.stderr)
        sys.exit(1)
    
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def print_pretty(result, source: str, no_color: bool, show_stats: bool):
    """Print results in a pretty format."""
    
    # Color codes
    if no_color:
        colors = {
            'green': '', 'blue': '', 'yellow': '', 'purple': '', 'cyan': '', 'red': '', 'reset': ''
        }
    else:
        colors = {
            'green': '\033[92m',
            'blue': '\033[94m', 
            'yellow': '\033[93m',
            'purple': '\033[95m',
            'cyan': '\033[96m',
            'red': '\033[91m',
            'reset': '\033[0m'
        }
    
    print(f"{colors['green']}✅ Successfully parsed {source}{colors['reset']}")
    print("=" * 60)
    
    # Count elements
    element_count = 0
    schema_count = 0
    attribute_count = 0
    
    # Process each element
    for key, value in result.items():
        element_count += 1
        
        if key.startswith('schema:'):
            schema_count += 1
            schema_name = key.replace('schema:', '')
            print(f"\n{colors['yellow']}📋 SCHEMA: {schema_name}{colors['reset']}")
            
            if hasattr(value, 'rules'):
                for rule in value.rules:
                    attrs = [f"@{attr.name}={attr.value}" for attr in rule.attributes]
                    attr_str = f" {colors['purple']}{' '.join(attrs)}{colors['reset']}" if attrs else ""
                    print(f"  • {colors['cyan']}{rule.key}{colors['reset']}: {colors['blue']}{rule.type}{colors['reset']}{attr_str}")
                    attribute_count += len(rule.attributes)
        else:
            print(f"\n{colors['blue']}📦 {key.upper()}:{colors['reset']}")
            print_value(value, "  ", colors)
            attribute_count += count_attributes(value)
    
    if show_stats:
        print(f"\n{colors['cyan']}📊 Statistics:{colors['reset']}")
        print(f"  • Total elements: {element_count}")
        print(f"  • Schemas: {schema_count}")
        print(f"  • Attributes: {attribute_count}")


def print_value(value, indent: str, colors: dict):
    """Print a Bring value with proper formatting."""
    from .parser import BringPrimitive, BringObject, BringArray
    
    if isinstance(value, BringPrimitive):
        print(f"{indent}{colors['green']}{repr(value.value)}{colors['reset']}")
    
    elif isinstance(value, BringObject):
        print(f"{indent}{{")
        for key, val in value.items.items():
            attrs = getattr(val, 'attributes', [])
            attr_str = f" {colors['purple']}[{', '.join(f'@{a.name}={a.value}' for a in attrs)}]{colors['reset']}" if attrs else ""
            
            if isinstance(val, BringPrimitive):
                print(f"{indent}  {colors['cyan']}{key}{colors['reset']}: {colors['green']}{repr(val.value)}{colors['reset']}{attr_str}")
            else:
                print(f"{indent}  {colors['cyan']}{key}{colors['reset']}:{attr_str}")
                print_value(val, indent + "    ", colors)
        print(f"{indent}}}")
    
    elif isinstance(value, BringArray):
        print(f"{indent}[")
        for i, item in enumerate(value.items):
            print(f"{indent}  [{i}]: ", end="")
            if isinstance(item, BringPrimitive):
                print(f"{colors['green']}{repr(item.value)}{colors['reset']}")
            else:
                print()
                print_value(item, indent + "    ", colors)
        print(f"{indent}]")


def count_attributes(value) -> int:
    """Count total attributes in a value recursively."""
    from .parser import BringObject, BringArray
    
    count = len(getattr(value, 'attributes', []))
    
    if isinstance(value, BringObject):
        for item in value.items.values():
            count += count_attributes(item)
    elif isinstance(value, BringArray):
        for item in value.items:
            count += count_attributes(item)
    
    return count


if __name__ == "__main__":
    main()
