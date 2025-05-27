#!/bin/bash

# Set the script directory and repository URL
SCRIPT_DIR="/home/pi300"
SCRIPT_NAME="auto_update_script.sh"
REPO_URL="https://github.com/tokual/pi300.git"
REPO_DIR="/home/pi300/pi300"
VENV_DIR="/home/pi300/pi300/venv"

# Navigate to the repository directory
cd "$REPO_DIR" || {
    echo "Repository directory not found. Cloning repository..."
    git clone "$REPO_URL" "$REPO_DIR"
    cd "$REPO_DIR"
    # Configure git pull behavior for new repos
    git config pull.rebase false
}

# Fetch the latest changes from remote
git fetch origin

# Check if there are updates available
LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main)

if [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
    echo "Updates found. Force resetting to remote changes..."
    
    # Force reset local changes to match remote (override any local modifications)
    git reset --hard origin/main
    
    # Copy the updated script to the execution location
    cp "$REPO_DIR/$SCRIPT_NAME" "$SCRIPT_DIR/$SCRIPT_NAME"
    chmod +x "$SCRIPT_DIR/$SCRIPT_NAME"
    
    # Update requirements.txt if Python files may have changed
    if [ -f "$REPO_DIR/update_requirements.sh" ]; then
        echo "Updating requirements.txt..."
        chmod +x "$REPO_DIR/update_requirements.sh"
        bash "$REPO_DIR/update_requirements.sh"
    fi
    
    echo "Script updated successfully."
else
    echo "No updates available."
fi

# Self-manage cron job - ensure it's set to run every 5 minutes
CRON_JOB="*/5 * * * * $SCRIPT_DIR/$SCRIPT_NAME >> /home/pi300/script.log 2>&1"

# Get current crontab for user
CURRENT_CRON=$(crontab -l 2>/dev/null || true)

# Check if the cron job is already present
if echo "$CURRENT_CRON" | grep -Fq "$SCRIPT_DIR/$SCRIPT_NAME"; then
    if echo "$CURRENT_CRON" | grep -Fq "$CRON_JOB"; then
        echo "Cron job already set correctly."
    else
        echo "Cron job needs updating..."
        NEW_CRON=$(echo "$CURRENT_CRON" | grep -v "$SCRIPT_DIR/$SCRIPT_NAME")
        
        if [ -n "$NEW_CRON" ]; then
            NEW_CRON="$NEW_CRON\n$CRON_JOB"
        else
            NEW_CRON="$CRON_JOB"
        fi
        
        echo -e "$NEW_CRON" | crontab -
        echo "Cron job updated: runs every 5 minutes with logging."
    fi
else
    echo "Adding new cron job..."
    if [ -n "$CURRENT_CRON" ]; then
        NEW_CRON="$CURRENT_CRON\n$CRON_JOB"
    else
        NEW_CRON="$CRON_JOB"
    fi
    
    echo -e "$NEW_CRON" | crontab -
    echo "Cron job added: runs every 5 minutes with logging."
fi

# Run the setup script to install dependencies
SETUP_SCRIPT="$REPO_DIR/setup.sh"
if [ -f "$SETUP_SCRIPT" ]; then
    echo "Running setup script to install dependencies..."
    chmod +x "$SETUP_SCRIPT"
    bash "$SETUP_SCRIPT"
else
    echo "Setup script not found, skipping dependency installation."
fi

# Execute the main Python script using virtual environment
echo "Executing main.py..."
cd "$REPO_DIR"

if [ -f "main.py" ]; then
    if [ -d "$VENV_DIR" ]; then
        echo "Using virtual environment to run main.py..."
        source "$VENV_DIR/bin/activate"
        python3 main.py
        deactivate
    else
        echo "Virtual environment not found, creating it first..."
        bash "$SETUP_SCRIPT"
        if [ -d "$VENV_DIR" ]; then
            source "$VENV_DIR/bin/activate"
            python3 main.py
            deactivate
        else
            echo "Failed to create virtual environment"
        fi
    fi
    echo "main.py execution completed."
else
    echo "Warning: main.py not found in repository."
fi

# Add timestamp to log
echo "Script execution completed at $(date)"
echo "----------------------------------------"
