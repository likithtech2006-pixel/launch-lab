# csvpeek

Preview huge CSV files in your terminal without loading them into memory.

[![PyPI](https://img.shields.io/pypi/v/csvpeek)](https://pypi.org/project/csvpeek/) [![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

`csvpeek` streams the first rows of a CSV, infers column types and prints an aligned table.
Works on multi-GB files in milliseconds.

## Quickstart

Requires Python 3.9+.

```bash
pip install csvpeek
csvpeek data.csv --rows 10
```

## Options

| Flag | Meaning |
|---|---|
| `--rows N` | rows to show (default 20) |
| `--types` | show inferred column types |
