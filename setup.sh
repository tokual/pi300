#!/bin/bash

# Directory of the repo
REPO_DIR="/home/pi300/pi300"
VENV_DIR="/home/pi300/pi300/venv"

cd "$REPO_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment and install dependencies
echo "Installing Python dependencies in virtual environment..."
source "$VENV_DIR/bin/activate"
pip install -r "$REPO_DIR/requirements.txt" --quiet
deactivate

echo "Dependencies installed successfully in virtual environment."
