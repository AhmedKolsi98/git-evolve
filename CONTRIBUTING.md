# Contributing to git-evolve

Thank you for your interest in contributing to git-evolve!

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/ahmedkolsi98/git-evolve.git
   cd git-evolve
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the package with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Install pre-commit hooks:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Running Tests

Run all tests:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest tests/ --cov=git_evolve --cov-report=html
```

## Code Style

This project uses:
- **Black** for code formatting (line length: 100)
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

Format your code:
```bash
black git_evolve tests
isort git_evolve tests
flake8 git_evolve tests
mypy git_evolve
```

Or use pre-commit to run all checks:
```bash
pre-commit run --all-files
```

## Adding New Features

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and add tests

3. Ensure all tests pass:
   ```bash
   pytest tests/ -v
   ```

4. Format and lint:
   ```bash
   black git_evolve tests
   flake8 git_evolve tests
   ```

5. Commit your changes:
   ```bash
   git add .
   git commit -m "Add your feature description"
   ```

6. Push to GitHub:
   ```bash
   git push origin feature/your-feature-name
   ```

7. Create a Pull Request

## Commit Message Convention

Use clear, descriptive commit messages:
- `Add file exclusion pattern support`
- `Fix binary file handling`
- `Improve error messages for invalid commits`
- `Add timeline feature`

## Reporting Issues

When reporting issues, please include:
- Python version
- Git version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
