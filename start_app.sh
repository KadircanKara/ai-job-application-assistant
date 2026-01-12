#!/bin/bash

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}--- 1. System Check ---${NC}"
if ! docker info > /dev/null 2>&1; then
  echo "❌ Error: Docker is NOT running."
  exit 1
fi

echo -e "${GREEN}--- 2. Starting Search Engine ---${NC}"
docker compose up -d 2>/dev/null || docker-compose up -d

echo -e "${GREEN}--- 3. Setting up Virtual Environment ---${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo -e "${GREEN}--- 4. Installing Dependencies ---${NC}"
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

# --- NEW: Install Browser for Scraper ---
echo -e "${GREEN}--- 4b. Installing Browser Engine ---${NC}"
playwright install chromium

echo -e "${GREEN}--- 5. Launching App ---${NC}"
python3 -m streamlit run app.py