#!/bin/bash
# WebSocket Infrastructure Setup Script

echo "========================================"
echo "BTC Arbitrage - WebSocket Setup"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  This script needs sudo access to install python3-websockets"
    echo "Please run with: sudo bash install_websocket.sh"
    echo "Or install manually: sudo apt-get install python3-websockets"
    exit 1
fi

echo "Step 1: Installing python3-websockets..."
apt-get update -qq
apt-get install -y python3-websockets

if [ $? -eq 0 ]; then
    echo "✅ python3-websockets installed"
else
    echo "❌ Installation failed"
    exit 1
fi

echo ""
echo "Step 2: Verifying installation..."
python3 -c "import websockets; print('✅ websockets module available')" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "❌ Verification failed"
    exit 1
fi

echo ""
echo "Step 3: Testing WebSocket infrastructure..."
cd "$(dirname "$0")/src"

echo "Running 30-second test..."
python3 test_websocket.py 30

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Review test results above"
echo "  2. Read src/README_WEBSOCKET.md for usage"
echo "  3. Try: python3 src/realtime_pipeline.py"
echo ""
