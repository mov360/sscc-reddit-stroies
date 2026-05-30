# RMIT Reddit Course Experience Extractor

A command-line tool for collecting Reddit posts and comments for CES-related analysis.

## Run the app

```bash
python main.py
```

## Developer commands

```bash
PYTHONPATH=src python -m rmit_ces_reddit_extractor.cli.menu validate
PYTHONPATH=src python -m rmit_ces_reddit_extractor.cli.menu keywords
PYTHONPATH=src python -m rmit_ces_reddit_extractor.cli.menu extract
PYTHONPATH=src python -m rmit_ces_reddit_extractor.cli.menu summary
```

## Main folders

- `src/rmit_ces_reddit_extractor/cli` contains menu and command-line interface code.
- `src/rmit_ces_reddit_extractor/backend` contains Reddit extraction logic.
- `src/rmit_ces_reddit_extractor/core` contains settings, runtime config, keywords, and dataset row helpers.
- `src/rmit_ces_reddit_extractor/reports` contains dataset summary/reporting code.
- `config` contains editable JSON configuration files.
- `data` stores generated CSV/JSON datasets.
- `logs` stores generated log files.
