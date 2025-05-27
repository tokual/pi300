#!/bin/bash

# Set the script directory and repository URL
SCRIPT_DIR="/home/pi300"
SCRIPT_NAME="auto_update_script.sh"
REPO_URL="https://github.com/tokual/pi300.git"
REPO_DIR="/home/pi300/pi300"

# Navigate to the repository directory
cd "$REPO_DIR" || {
    echo "Repository directory not found. Cloning repository..."
    git clone "$REPO_URL" "$REPO_DIR"
    cd "$REPO_DIR"
}

# Fetch the latest changes from remote
git fetch origin

# Check if there are updates available
LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main)

if [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
    echo "Updates found. Pulling latest changes..."
    git pull origin main
    
    # Copy the updated script to the execution location
    cp "$REPO_DIR/$SCRIPT_NAME" "$SCRIPT_DIR/$SCRIPT_NAME"
    chmod +x "$SCRIPT_DIR/$SCRIPT_NAME"
    
    echo "Script updated successfully."
else
    echo "No updates available."
fi

# Your additional tasks can go here
# For example, future Python script execution:
# python3 /path/to/your/python_script.py
