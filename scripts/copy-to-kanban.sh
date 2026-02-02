#!/bin/bash
# Copy kanban files from workspace to actual kanban location
rsync -a --delete /home/clawdbot/clawd/kanban-tasks/ /home/clawdbot/kanban/tasks/
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Synced kanban-tasks to kanban/tasks"
