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

# Self-manage cron job - ensure it's set to run every 2 minutes
CRON_JOB="*/3 * * * * $SCRIPT_DIR/$SCRIPT_NAME"

# Get current crontab for user
CURRENT_CRON=$(crontab -l 2>/dev/null || true)

# Check if the cron job is already present
if echo "$CURRENT_CRON" | grep -Fq "$CRON_JOB"; then
    echo "Cron job already set correctly."
else
    # Remove any existing line that runs this script (in case timing changed)
    NEW_CRON=$(echo "$CURRENT_CRON" | grep -v "$SCRIPT_DIR/$SCRIPT_NAME")
    
    # Add the new cron job line
    if [ -n "$NEW_CRON" ]; then
        NEW_CRON="$NEW_CRON\n$CRON_JOB"
    else
        NEW_CRON="$CRON_JOB"
    fi
    
    # Install the new crontab
    echo -e "$NEW_CRON" | crontab -
    echo "Cron job updated/added: runs every 2 minutes."
fi

# Execute the main Python script
echo "Executing main.py..."
cd "$REPO_DIR"

if [ -f "main.py" ]; then
    python3 main.py
    echo "main.py execution completed."
else
    echo "Warning: main.py not found in repository."
fi
