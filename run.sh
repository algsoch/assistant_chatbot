#!/bin/bash
# run.sh - Quick start script for TDS Assistant

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${YELLOW}⚠ No venv found. Creating one...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                           ║${NC}"
echo -e "${BLUE}║   🎯 TDS Assistant v1.0.0                                 ║${NC}"
echo -e "${BLUE}║   AI-Powered Question Answering System                    ║${NC}"
echo -e "${BLUE}║                                                           ║${NC}"
echo -e "${BLUE}╠═══════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║                                                           ║${NC}"
echo -e "${BLUE}║   🌐 Server: http://localhost:8000                        ║${NC}"
echo -e "${BLUE}║   📖 API Docs: http://localhost:8000/docs                 ║${NC}"
echo -e "${BLUE}║                                                           ║${NC}"
echo -e "${BLUE}║   Press Ctrl+C to stop                                    ║${NC}"
echo -e "${BLUE}║                                                           ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Run the application
python -m uvicorn vicky_app:app --reload --host 0.0.0.0 --port 8000
