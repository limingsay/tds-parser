"""tds-parser: extract structured property tables from plastics TDS documents."""

from .parse import Property, parse_text, normalize_name, to_markdown, to_csv, to_json  # noqa: F401

__version__ = "0.1.0"
