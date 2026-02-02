#!/bin/bash
# MediaCrawler Setup Script for XHS Cover Research
# Run this on the server (45.55.78.247) as clawdbot user
#
# Usage: bash setup-mediacrawler.sh

set -e

INSTALL_DIR="$HOME/MediaCrawler"
VENV_DIR="$INSTALL_DIR/venv"

echo "🔧 Setting up MediaCrawler for XHS cover research..."

# 1. Clone repo
if [ -d "$INSTALL_DIR" ]; then
    echo "📁 MediaCrawler already exists, pulling latest..."
    cd "$INSTALL_DIR" && git pull
else
    echo "📥 Cloning MediaCrawler..."
    git clone https://github.com/NanmiCoder/MediaCrawler.git "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# 2. Create venv
if [ ! -d "$VENV_DIR" ]; then
    echo "🐍 Creating Python venv..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# 3. Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# 4. Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium
playwright install-deps chromium

# 5. Configure for XHS search
cat > config/base_config.py << 'PYCONFIG'
PLATFORM = "xhs"
KEYWORDS = "护肤好物推荐,护肤测评,北美护肤,抗老护肤,护肤routine"
LOGIN_TYPE = "cookie"  # Use cookie login
COOKIES = ""  # Will be set via env or manually
CRAWLER_TYPE = "search"
ENABLE_IP_PROXY = False
HEADLESS = True  # Run headless on server
SAVE_LOGIN_STATE = True
ENABLE_CDP_MODE = False
CRAWLER_MAX_NOTES_COUNT = 100
PYCONFIG

echo ""
echo "✅ MediaCrawler installed!"
echo ""
echo "Next steps:"
echo "  1. Set your XHS cookie:"
echo "     export XHS_COOKIE='your_cookie_here'"
echo "  2. Run the crawler:"
echo "     cd $INSTALL_DIR && source venv/bin/activate"
echo "     python main.py"
echo ""
echo "  Or for cookie login via QR code (needs display):"
echo "     Change HEADLESS=False in config/base_config.py"
echo "     python main.py"
