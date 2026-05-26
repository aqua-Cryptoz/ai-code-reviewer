# 🔍 AI Code Reviewer

**AI-powered code review tool** that analyzes Python code for bugs, security vulnerabilities, style issues, and performance concerns using LLMs (powered by Xiaomi MiMo).

## Features

- **🤖 LLM-Powered Analysis** — Deep code understanding via MiMo models
- **🔒 Security Scanning** — Detects `eval()`, `exec()`, hardcoded secrets, SQL injection patterns
- **📊 Complexity Metrics** — Cyclomatic complexity via `radon`
- **🎨 Style Detection** — Naming conventions, docstrings, line length, import ordering
- **📝 Rich Reports** — Markdown review reports with actionable suggestions
- **🖥️ Beautiful CLI** — Rich terminal output with syntax highlighting

## Quick Start

```bash
pip install -r requirements.txt

# Demo mode — see a sample review
python main.py --demo

# Review a single file
python main.py my_script.py

# Review entire directory
python main.py src/

# Use MiMo API (set key first)
export MIMO_API_KEY="your-key-here"
python main.py my_script.py --provider mimo
```

## Architecture

```
ai-code-reviewer/
├── main.py              # CLI entry point
├── reviewer.py          # Core CodeReviewer class
├── report.py            # Markdown report generator
├── analyzers/
│   ├── complexity.py    # Cyclomatic complexity analysis
│   ├── security.py      # Security pattern detection
│   └── style.py         # Style & convention checks
└── providers/
    ├── base.py          # Abstract LLM provider
    └── mimo_provider.py # Xiaomi MiMo integration
```

## MiMo Integration

Uses **Xiaomi MiMo** LLM for intelligent code analysis. Set `MIMO_API_KEY` environment variable or pass `--api-key` flag.

## License

MIT
