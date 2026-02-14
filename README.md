# 🧬 git-evolve

> Measure code evolution from any base commit.

A powerful CLI tool that analyzes how much your codebase has evolved since a specific starting point (commit, tag, or branch). Perfect for tracking development progress, measuring refactoring impact, or understanding code churn over time.

## ✨ Features

- **Precise Evolution Metrics** - Calculate the percentage of code changed since a base commit using git blame
- **Per-File Analysis** - Identify which files have evolved the most
- **Fast Parallel Processing** - Analyze large repositories efficiently with multi-worker support
- **Flexible Output** - Beautiful ASCII reports, JSON export, or minimal output
- **Multiple Formats** - Works with commit hashes, tags, branch names, and relative references (e.g., `HEAD~20`)

## 📋 Requirements

- Python 3.8+
- Git 2.0+

## 📦 Installation

### From Source

```bash
git clone https://github.com/yourusername/git-evolve.git
cd git-evolve
pip install -e .
```

### Verify Installation

```bash
git-evolve --help
```

## 🚀 Quick Start

```bash
# Measure evolution since a release tag
git-evolve --base v1.0.0

# Analyze last 20 commits
git-evolve --base HEAD~20

# Show per-file breakdown
git-evolve --base main --files

# Export results as JSON
git-evolve --base v2.0.0 --json
```

## 📖 Usage Guide

### Basic Command

```bash
git-evolve --base <commit-reference>
```

### Options

| Option | Description |
|--------|-------------|
| `--base` (required) | Base commit/tag/branch reference to measure evolution from |
| `--files` | Show top 10 evolved files with line counts |
| `--json` | Output results in JSON format (useful for scripts/integrations) |
| `--quiet` | Minimal output: just the evolution percentage |
| `--no-parallel` | Disable parallel processing (useful for debugging) |
| `--workers` | Number of parallel workers (default: 4) |
| `--timeline` | Show timeline of commits (coming soon) |

### Examples

#### 1. Report Since Last Release

```bash
git-evolve --base v1.5.0
```

**Output:**
```
────────────────────────────────────────────────

  🧬 Git Evolve Report: my-project

  Base commit: abc1234d

────────────────────────────────────────────────

  📊 Code Statistics
  ────────────────────────────────────────
  Total Lines                    45,230
  Base Lines Surviving           28,145
  Evolved Lines                  17,085
  Files Analyzed                 142

  📈 Evolution: 37.78% | Survival: 62.22%
  [███████████████░░░░░░░░░░░░░░░░░░░░░░░░]

  📁 Top Evolved Files
  ────────────────────────────────────────

   1. src/core/engine.py
      ███████░░░░░░░░░░░░ 67.34% (1,245 lines)

   2. src/utils/helpers.py
      █████░░░░░░░░░░░░░░ 45.21% (892 lines)

   3. src/api/handlers.py
      ████░░░░░░░░░░░░░░░ 38.90% (756 lines)

────────────────────────────────────────────────
```

#### 2. Get JSON Output for CI/CD

```bash
git-evolve --base main --json | jq '.evolution_percent'
```

```json
37.78
```

#### 3. Minimal Output for Scripts

```bash
git-evolve --base v2.0.0 --quiet
```

```
42.15%
```

#### 4. Analyze with Custom Worker Count

```bash
git-evolve --base HEAD~50 --files --workers 8
```

## 🔍 Understanding the Metrics

### Evolution Percent
Percentage of code lines that are **different** from the base commit. This includes:
- New lines added after the base commit
- Modified lines
- Deleted lines count as evolved in their original files

Formula: `(evolved_lines / total_lines) × 100`

### Survival Percent
Percentage of code lines that are **unchanged** since the base commit.

Formula: `100 - evolution_percent`

### Base Lines Surviving
Total number of lines that remain unchanged from the base commit.

## 🛠️ Development

### Setup Development Environment

```bash
git clone https://github.com/yourusername/git-evolve.git
cd git-evolve
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/
pytest tests/ -v  # verbose
pytest tests/ --cov=git_evolve  # with coverage
```

### Code Formatting & Linting

```bash
black git_evolve tests
flake8 git_evolve tests
mypy git_evolve
```

### Project Structure

```
git-evolve/
├── git_evolve/
│   ├── __init__.py          # Package initialization
│   ├── analyzer.py          # Core analysis logic
│   └── cli.py              # Command-line interface
├── tests/                   # Test suite
├── pyproject.toml          # Project metadata and dependencies
├── README.md               # This file
└── LICENSE                 # MIT License
```

## 📊 Use Cases

### 1. Track Development Progress
Monitor how much of your codebase is new/modified versus the last major release.

```bash
git-evolve --base v1.0.0 --quiet
# Output: 45.32%
# Meaning: 45% of the code is different since v1.0.0
```

### 2. Measure Refactoring Impact
See how much code was touched during a major refactoring effort.

```bash
git-evolve --base refactor-start-commit --files
```

### 3. Sprint Velocity
Track code changes over sprint cycles.

```bash
git-evolve --base sprint-5-start
```

### 4. Automated Monitoring
Integrate into CI/CD pipelines to track evolution metrics.

```bash
# .github/workflows/metrics.yml
- name: Track code evolution
  run: |
    EVOLUTION=$(git-evolve --base main --quiet)
    echo "Code Evolution: $EVOLUTION"
```

## ⚙️ Performance Tips

- **Large Repositories**: Use `--workers` to increase parallel processing
  ```bash
  git-evolve --base main --workers 16
  ```

- **Network Repositories**: Run locally or use `--no-parallel` if network lag causes issues

- **Memory Constraints**: Use `--no-parallel` to reduce memory usage

## 🐛 Troubleshooting

### "fatal: Not a git repository"
- Ensure you're in a git repository directory
- Check: `git rev-parse --show-toplevel`

### "fatal: bad revision"
- Verify the base commit/tag exists
- Check: `git log --oneline -5`

### Slow Performance
- Try: `git-evolve --base main --no-parallel`
- Or adjust workers: `git-evolve --base main --workers 2`

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details

## 👤 Author

Ahmed Kolsi

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📚 See Also

- [git-stats](https://github.com/tomgi/git_stats) - Visualize git repo statistics
- [git-cloc](https://github.com/AlDanial/cloc) - Count lines of code
- [gitpython](https://gitpython.readthedocs.io/) - Python git library
