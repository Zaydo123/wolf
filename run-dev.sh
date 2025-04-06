#!/bin/bash

# Terminal colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=======================================${NC}"
echo -e "${GREEN}Starting Wolf App in Development Mode${NC}"
echo -e "${BLUE}=======================================${NC}"

# Check if the ports are already in use
backend_port_check=$(lsof -i:8000 -t)
frontend_port_check=$(lsof -i:3000 -t)

if [ ! -z "$backend_port_check" ]; then
    echo -e "${RED}Port 8000 is already in use. Kill the process? (y/n)${NC}"
    read kill_backend
    if [ "$kill_backend" = "y" ]; then
        kill -9 $backend_port_check
        echo -e "${GREEN}Backend process killed${NC}"
    else
        echo -e "${YELLOW}Backend will not start - port in use${NC}"
    fi
fi

if [ ! -z "$frontend_port_check" ]; then
    echo -e "${RED}Port 3000 is already in use. Kill the process? (y/n)${NC}"
    read kill_frontend
    if [ "$kill_frontend" = "y" ]; then
        kill -9 $frontend_port_check
        echo -e "${GREEN}Frontend process killed${NC}"
    else
        echo -e "${YELLOW}Frontend will not start - port in use${NC}"
    fi
fi

# Start backend in a new terminal tab
echo -e "${GREEN}Starting backend on port 8000...${NC}"
osascript -e 'tell application "Terminal" to do script "cd '$(pwd)'/backend && python -m app.run_app"'

# Start frontend in a new terminal tab
echo -e "${GREEN}Starting frontend on port 3000...${NC}"
osascript -e 'tell application "Terminal" to do script "cd '$(pwd)'/frontend && npm start"'

echo -e "${GREEN}Development environment started!${NC}"
echo -e "${BLUE}=======================================${NC}"
echo -e "${YELLOW}Frontend:${NC} http://localhost:3000"
echo -e "${YELLOW}Backend:${NC} http://localhost:8000"
echo -e "${YELLOW}API Docs:${NC} http://localhost:8000/docs"
echo -e "${BLUE}=======================================${NC}"