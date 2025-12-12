#!/usr/bin/env python3
"""
Generate a new Datasette plugin project structure.

Usage:
    python init_plugin.py <plugin-name> [--path <output-dir>]

Example:
    python init_plugin.py datasette-my-feature --path /home/user/projects
"""

import argparse
import os
import sys
from pathlib import Path


def create_plugin(name: str, output_dir: Path) -> None:
    """Create a new Datasette plugin project."""
    
    # Validate name
    if not name.startswith("datasette-"):
        print(f"Warning: Plugin name should start with 'datasette-'")
    
    # Convert name to module name (hyphens to underscores)
    module_name = name.replace("-", "_")
    
    # Create directory structure
    plugin_dir = output_dir / name
    module_dir = plugin_dir / module_name
    tests_dir = plugin_dir / "tests"
    
    for d in [plugin_dir, module_dir, tests_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    # Create pyproject.toml
    pyproject = f'''[project]
name = "{name}"
version = "0.1.0"
description = "A Datasette plugin"
readme = "README.md"
requires-python = ">=3.10"
license = {{text = "Apache-2.0"}}
authors = [
    {{name = "Your Name", email = "you@example.com"}}
]
dependencies = [
    "datasette"
]
[dependency-groups]
dev = [
    "pytest",
    "pytest-asyncio"
]

[project.entry-points.datasette]
{module_name.replace("datasette_", "")} = "{module_name}"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
'''
    (plugin_dir / "pyproject.toml").write_text(pyproject)
    
    # Create README.md
    readme = f'''# {name}

A Datasette plugin.

## Installation

```bash
pip install {name}
```

Or install directly from this repository:

```bash
pip install -e .
```

## Usage

This plugin adds [describe functionality here].

## Configuration

Add to your `datasette.yaml`:

```yaml
plugins:
  {name}:
    option1: value1
```

## Development

```bash
pip install -e ".[test]"
pytest
```
'''
    (plugin_dir / "README.md").write_text(readme)
    
    # Create main module __init__.py
    init_py = f'''"""
{name}

A Datasette plugin.
"""

from datasette import hookimpl

__version__ = "0.1.0"


@hookimpl
def prepare_connection(conn):
    """Register custom SQL functions."""
    # Example: Register a custom function
    # conn.create_function("my_function", 1, lambda x: x.upper())
    pass


# Uncomment and customize the hooks you need:

# @hookimpl
# def register_routes():
#     """Register custom URL routes."""
#     return [
#         (r"^/-/my-page$", my_page_view),
#     ]


# async def my_page_view(datasette, request):
#     from datasette import Response
#     return Response.html("<h1>My Custom Page</h1>")


# @hookimpl
# def startup(datasette):
#     """Run on server startup."""
#     async def inner():
#         config = datasette.plugin_config("{name}") or {{}}
#         # Initialize plugin
#         pass
#     return inner


# @hookimpl
# def menu_links(datasette, actor):
#     """Add items to the navigation menu."""
#     return [
#         {{"href": datasette.urls.path("/-/my-page"), "label": "My Feature"}}
#     ]


# @hookimpl
# def render_cell(value, column, table, database, datasette, request):
#     """Customize cell rendering in table view."""
#     return None  # Return None to use default rendering
'''
    (module_dir / "__init__.py").write_text(init_py)
    
    # Create tests/__init__.py
    (tests_dir / "__init__.py").write_text("")
    
    # Create test file
    test_py = f'''"""Tests for {name}."""

from datasette.app import Datasette
import pytest


@pytest.mark.asyncio
async def test_plugin_is_installed():
    """Test that the plugin is properly installed."""
    datasette = Datasette(memory=True)
    response = await datasette.client.get("/-/plugins.json")
    assert response.status_code == 200
    installed_plugins = {{p["name"] for p in response.json()}}
    assert "{name}" in installed_plugins


# Add more tests for your plugin functionality:

# @pytest.mark.asyncio
# async def test_custom_route():
#     datasette = Datasette(memory=True)
#     response = await datasette.client.get("/-/my-page")
#     assert response.status_code == 200


# @pytest.mark.asyncio
# async def test_custom_sql_function():
#     datasette = Datasette(memory=True)
#     response = await datasette.client.get(
#         "/_memory.json?sql=select+my_function('test')"
#     )
#     assert response.status_code == 200
'''
    (tests_dir / f"test_{module_name}.py").write_text(test_py)
    
    # Create pytest.ini
    pytest_ini = '''[pytest]
asyncio_mode = auto
'''
    (plugin_dir / "pytest.ini").write_text(pytest_ini)
    
    # Create .gitignore
    gitignore = '''__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.eggs/
*.egg
.pytest_cache/
.coverage
htmlcov/
.venv/
venv/
'''
    (plugin_dir / ".gitignore").write_text(gitignore)
    
    print(f"Created plugin at: {plugin_dir}")
    print(f"\nNext steps:")
    print(f"  cd {plugin_dir}")
    print(f"  pip install -e '.[test]'")
    print(f"  pytest")


def main():
    parser = argparse.ArgumentParser(description="Create a new Datasette plugin")
    parser.add_argument("name", help="Plugin name (e.g., datasette-my-feature)")
    parser.add_argument("--path", default=".", help="Output directory")
    
    args = parser.parse_args()
    output_dir = Path(args.path).resolve()
    
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    
    create_plugin(args.name, output_dir)


if __name__ == "__main__":
    main()
