#!/bin/bash
set -e

# Function to display help
show_help() {
    echo "Available commands:"
    echo "  test       - Run tests"
    echo "  coverage   - Run tests with coverage"
    echo "  lint       - Run ruff linter"
    echo "  format     - Run ruff formatter"
    echo "  shell      - Start interactive shell"
    echo "  help       - Show this help message"
}

# Main command handling
case "$1" in
    test)
        echo "Running tests..."
        uv run pytest tests/ -v
        ;;
    coverage)
        echo "Running tests with coverage..."
        uv run pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
        ;;
    lint)
        echo "Running ruff linter..."
        uv run ruff check .
        ;;
    format)
        echo "Running ruff formatter..."
        uv run ruff format .
        ;;
    shell)
        echo "Starting interactive shell..."
        exec /bin/bash
        ;;
    help|*)
        show_help
        ;;
esac
