#!/bin/bash

# Directory of the repo
REPO_DIR="/home/pi300/pi300"
VENV_DIR="/home/pi300/pi300/venv"

cd "$REPO_DIR"

echo "Updating requirements.txt..."

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment and install pipreqs
source "$VENV_DIR/bin/activate"
pip install pipreqs --quiet

# Generate requirements.txt based on actual imports in .py files
pipreqs . --force --print > requirements_new.txt

# Check if generation was successful
if [ -f "requirements_new.txt" ] && [ -s "requirements_new.txt" ]; then
    # Replace the old requirements.txt
    mv requirements_new.txt requirements.txt
    echo "requirements.txt updated successfully based on actual imports"
    
    # Show what was generated
    echo "Current requirements:"
    cat requirements.txt
else
    echo "Failed to generate requirements.txt"
    # Clean up failed attempt
    [ -f "requirements_new.txt" ] && rm requirements_new.txt
fi

deactivate
