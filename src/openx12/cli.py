"""
openx12 CLI - Parse X12 healthcare EDI files from the command line
"""

import argparse
import json
import sys
from pathlib import Path

from . import x835, x837p, x837i


PARSERS = {
    "835": x835.parse,
    "837p": x837p.parse,
    "837i": x837i.parse,
}


def detect_file_type(content: str) -> str | None:
    """Auto-detect X12 file type from content."""
    if "ST*835*" in content or "ST*835~" in content:
        return "835"
    elif "ST*837*" in content:
        if "005010X223" in content:
            return "837i"
        return "837p"
    return None


def main():
    parser = argparse.ArgumentParser(
        prog="openx12",
        description="Parse X12 healthcare EDI files (835, 837P, 837I)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # parse command
    parse_cmd = subparsers.add_parser("parse", help="Parse an EDI file")
    parse_cmd.add_argument("file", help="EDI file to parse (or - for stdin)")
    parse_cmd.add_argument(
        "-t", "--type",
        choices=["835", "837p", "837i", "auto"],
        default="auto",
        help="File type (default: auto-detect)"
    )
    parse_cmd.add_argument(
        "-f", "--format",
        choices=["json", "table", "summary"],
        default="json",
        help="Output format (default: json)"
    )
    parse_cmd.add_argument(
        "-o", "--output",
        help="Output file (default: stdout)"
    )
    parse_cmd.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="Pretty print JSON (default: true)"
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version="%(prog)s 0.2.1"
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "parse":
        if args.file == "-":
            content = sys.stdin.read()
        else:
            path = Path(args.file)
            if not path.exists():
                print(f"Error: File not found: {args.file}", file=sys.stderr)
                sys.exit(1)
            content = path.read_text()

        file_type = args.type
        if file_type == "auto":
            file_type = detect_file_type(content)
            if file_type is None:
                print("Error: Could not auto-detect file type. Use --type to specify.", file=sys.stderr)
                sys.exit(1)

        parse_func = PARSERS[file_type]
        parsed = parse_func(content)

        if args.format == "json":
            result = parsed.json()
            indent = 2 if args.pretty else None
            output = json.dumps(result, indent=indent, default=str)
        elif args.format == "table":
            output = parsed.table()
        else:
            result = parsed.summary()
            indent = 2 if args.pretty else None
            output = json.dumps(result, indent=indent, default=str)

        if args.output:
            Path(args.output).write_text(output)
            print(f"Output written to {args.output}", file=sys.stderr)
        else:
            print(output)


if __name__ == "__main__":
    main()
