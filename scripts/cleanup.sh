#!/bin/bash
CONFIG_DIR="$HOME/.nexify"
LOG_FILE="$CONFIG_DIR/logs/uninstall.log"

echo "This script will delete all NexifyTool data in $CONFIG_DIR, including database and media files."
echo "This action cannot be undone. Continue? [y/N]"
read -r response
if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
    mkdir -p "$CONFIG_DIR/logs"
    echo "$(date '+%Y-%m-%d %H:%M:%S') Attempting to delete $CONFIG_DIR" >> "$LOG_FILE"
    rm -rf "$CONFIG_DIR" && {
        echo "$(date '+%Y-%m-%d %H:%M:%S') Successfully deleted $CONFIG_DIR" >> "$LOG_FILE"
        echo "Data deleted successfully."
    } || {
        echo "$(date '+%Y-%m-%d %H:%M:%S') Failed to delete $CONFIG_DIR" >> "$LOG_FILE"
        echo "Failed to delete $CONFIG_DIR. Please delete it manually."
    }
else
    echo "Cleanup aborted."
fi