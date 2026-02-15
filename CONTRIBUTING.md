# Contributing to Evolution Gaming Baccarat Scraper

Thank you for considering contributing to this project! We welcome contributions of all kinds.

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Git

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/Midan14/EVOLUTION-SCRAPER.git
cd EVOLUTION-SCRAPER

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Install Playwright browsers
playwright install chromium

# Copy environment template
cp .env.example .env
# Edit .env with your configuration
```

## 🔧 Development Workflow

### Running Tests

```bash
# Run all tests
pytest -q

# Run specific test file
pytest tests/test_database.py -v

# Run with coverage
pytest --cov=src --cov-report=html
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Lint code with ruff
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Security audit
pip-audit -r requirements.txt
```

### Making Changes

1. **Create a branch** for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards:
   - Follow PEP 8 style guide (enforced by ruff)
   - Line length: 100 characters max
   - Use type hints where appropriate
   - Add docstrings to functions and classes
   - Write tests for new functionality

3. **Test your changes**:
   ```bash
   # Run tests
   pytest -q
   
   # Check linting
   ruff check .
   
   # Security audit
   pip-audit -r requirements.txt
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```
   
   Use conventional commit messages:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `test:` - Test changes
   - `refactor:` - Code refactoring
   - `chore:` - Maintenance tasks

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request** on GitHub

## 📝 Coding Standards

### Python Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Keep functions focused and single-purpose
- Prefer composition over inheritance

### Type Hints

Use type hints for function parameters and return values:

```python
from typing import Dict, List, Optional

def process_results(results: List[Dict[str, Any]]) -> Optional[str]:
    """Process game results and return summary."""
    ...
```

### Docstrings

Use clear docstrings for all public functions:

```python
def analyze_pattern(history: List[str]) -> Dict[str, float]:
    """
    Analyze baccarat pattern from game history.
    
    Args:
        history: List of game results ('P', 'B', 'T')
        
    Returns:
        Dictionary with pattern analysis metrics
    """
    ...
```

### Testing

- Write tests for all new functionality
- Use pytest fixtures for setup/teardown
- Test both success and failure cases
- Aim for good test coverage (>80%)

## 🐛 Reporting Bugs

When reporting bugs, please include:

1. **Description** - Clear description of the issue
2. **Steps to reproduce** - How to trigger the bug
3. **Expected behavior** - What should happen
4. **Actual behavior** - What actually happens
5. **Environment** - OS, Python version, etc.
6. **Logs** - Relevant error messages or logs

## 💡 Suggesting Features

We welcome feature suggestions! Please:

1. Check if the feature has already been requested
2. Describe the use case and benefits
3. Provide implementation ideas if possible

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## ❓ Questions?

If you have questions, please:

1. Check existing issues and discussions
2. Review the documentation in README.md
3. Open a new issue with your question

Thank you for contributing! 🎉
