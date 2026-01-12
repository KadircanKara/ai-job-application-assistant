#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}--- 1. Pre-Flight Checks ---${NC}"

# Check for .env file (Critical for API keys)
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file is missing!${NC}"
    echo "Please create a .env file in the project root with FIRECRAWL_API_KEY and OPENROUTER_API_KEY."
    exit 1
fi

# Check for Docker (Required for SearXNG)
if ! docker info > /dev/null 2>&1; then
  echo -e "${RED}❌ Error: Docker is NOT running.${NC}"
  echo "Please open Docker Desktop and wait for the engine to start."
  exit 1
fi

echo -e "${GREEN}--- 2. Starting Search Engine (SearXNG) ---${NC}"

# Save the current directory so we can return later
PROJECT_ROOT=$(pwd)
CURRENT_FOLDER_NAME=$(basename "$PROJECT_ROOT")

# LOGIC: Find where to run Docker
if [ "$CURRENT_FOLDER_NAME" == "searxng-docker" ]; then
    # Case A: We are already inside the folder
    echo -e "${BLUE}ℹ️  Already inside 'searxng-docker' folder.${NC}"
    docker compose up -d 2>/dev/null || docker-compose up -d
    
    # Move up one level to find app.py for later steps
    cd ..
    
elif [ -d "searxng-docker" ]; then
    # Case B: We are in root, and the folder exists
    echo -e "${BLUE}ℹ️  Navigating into 'searxng-docker' folder...${NC}"
    cd searxng-docker
    
    # Start Docker
    docker compose up -d 2>/dev/null || docker-compose up -d
    
    # Return to project root
    cd "$PROJECT_ROOT"
    
elif [ -f "docker-compose.yml" ]; then
    # Case C: docker-compose.yml is in the root (Legacy setup)
    echo -e "${BLUE}ℹ️  Found docker config in root.${NC}"
    docker compose up -d 2>/dev/null || docker-compose up -d
    
else
    echo -e "${RED}❌ Error: Could not find 'searxng-docker' folder or 'docker-compose.yml'.${NC}"
    exit 1
fi

# Ensure we are back in the project root before Python setup
cd "$PROJECT_ROOT" || exit

echo -e "${GREEN}--- 3. Setting up Python Environment ---${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating new virtual environment..."
    python3 -m venv venv
fi

# Activate environment
source venv/bin/activate

echo -e "${GREEN}--- 4. Installing Dependencies ---${NC}"

# 1. Upgrade pip (Show output)
echo "Upgrading pip..."
pip install --upgrade pip

# 2. Install requirements (Show detailed output)
echo "Installing libraries (this may take a minute)..."
pip install -r requirements.txt

echo -e "${GREEN}--- 5. Launching App ---${NC}"
echo "----------------------------------------------------------------"
echo "Local Search Engine: http://localhost:8080"
echo "AI Job Agent:        http://localhost:8501"
echo "----------------------------------------------------------------"

python3 -m streamlit run app.py