#!/bin/bash
# ============================================
# OpenClaw Server Hardening Script
# ⚠️ READ BEFORE RUNNING!
# This script will:
#   1. Install & enable UFW firewall
#   2. Harden SSH (disable password, change port)
#   3. Install fail2ban
#   4. Guide Tailscale install
#
# Usage: sudo bash harden.sh
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🔒 OpenClaw Server Hardening${NC}"
echo "=========================================="
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root: sudo bash harden.sh${NC}"
    exit 1
fi

# ============================================
# STEP 1: UFW Firewall
# ============================================
echo -e "${YELLOW}[1/4] Firewall (UFW)${NC}"

if ! command -v ufw &>/dev/null; then
    echo "Installing UFW..."
    apt-get update -qq && apt-get install -y ufw
fi

# Get current SSH port before changing anything
# Get current SSH port — grep may fail if Port not set, so default to 22
CURRENT_SSH_PORT=$(grep -E "^Port " /etc/ssh/sshd_config 2>/dev/null | awk '{print $2}')
CURRENT_SSH_PORT="${CURRENT_SSH_PORT:-22}"
NEW_SSH_PORT="${SSH_PORT:-2222}"

echo "Setting up firewall rules..."
ufw default deny incoming
ufw default allow outgoing

# Allow current SSH port (so we don't lock ourselves out!)
ufw allow "$CURRENT_SSH_PORT"/tcp comment "SSH current"
# Also allow new SSH port if different
if [ "$CURRENT_SSH_PORT" != "$NEW_SSH_PORT" ]; then
    ufw allow "$NEW_SSH_PORT"/tcp comment "SSH new port"
fi

# DO NOT open gateway port to public
# Gateway should only be accessible via loopback or Tailscale

echo ""
echo -e "${YELLOW}⚠️  About to enable firewall. This will block all incoming${NC}"
echo -e "${YELLOW}   connections except SSH on port $CURRENT_SSH_PORT (and $NEW_SSH_PORT if different).${NC}"
echo ""
read -p "Enable UFW now? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ufw --force enable
    echo -e "${GREEN}✅ Firewall enabled${NC}"
    ufw status verbose
else
    echo "Skipped. Run 'sudo ufw enable' when ready."
fi

# ============================================
# STEP 2: SSH Hardening
# ============================================
echo ""
echo -e "${YELLOW}[2/4] SSH Hardening${NC}"

SSHD_CONFIG="/etc/ssh/sshd_config"
BACKUP="/etc/ssh/sshd_config.backup.$(date +%Y%m%d%H%M)"

# Backup first
cp "$SSHD_CONFIG" "$BACKUP"
echo "  Backed up to $BACKUP"

# Ensure SSH key exists for clawdbot user
CLAWDBOT_HOME=$(getent passwd clawdbot | cut -d: -f6 2>/dev/null || echo "/home/clawdbot")
if [ ! -f "$CLAWDBOT_HOME/.ssh/authorized_keys" ]; then
    echo -e "${RED}⚠️  No SSH keys found for clawdbot user!${NC}"
    echo "  You MUST add your SSH public key before disabling password auth."
    echo "  Run: ssh-copy-id clawdbot@$(hostname -I | awk '{print $1}')"
    echo ""
    read -p "Do you have SSH keys set up? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "  ❌ Skipping SSH hardening — add keys first!"
        echo "  On your LOCAL machine, run:"
        echo "    ssh-keygen -t ed25519  (if you don't have a key)"
        echo "    ssh-copy-id clawdbot@$(hostname -I | awk '{print $1}')"
        SKIP_SSH=1
    fi
fi

if [ -z "$SKIP_SSH" ]; then
    echo "  Applying SSH hardening..."
    
    # Function to set or add config
    set_ssh_config() {
        local key=$1 val=$2
        if grep -qE "^#?${key}" "$SSHD_CONFIG"; then
            sed -i "s/^#*${key}.*/${key} ${val}/" "$SSHD_CONFIG"
        else
            echo "${key} ${val}" >> "$SSHD_CONFIG"
        fi
    }
    
    set_ssh_config "Port" "$NEW_SSH_PORT"
    set_ssh_config "PermitRootLogin" "no"
    set_ssh_config "PasswordAuthentication" "no"
    set_ssh_config "PubkeyAuthentication" "yes"
    set_ssh_config "MaxAuthTries" "3"
    set_ssh_config "X11Forwarding" "no"
    set_ssh_config "AllowAgentForwarding" "no"
    
    echo -e "  ${GREEN}✅ SSH hardened:${NC}"
    echo "    Port: $NEW_SSH_PORT"
    echo "    PasswordAuth: no"
    echo "    RootLogin: no"
    echo "    MaxAuthTries: 3"
    
    # Test config before restarting
    if sshd -t 2>/dev/null; then
        echo ""
        echo -e "${YELLOW}⚠️  About to restart SSH on port $NEW_SSH_PORT${NC}"
        echo -e "${YELLOW}   KEEP THIS SESSION OPEN and test new connection first!${NC}"
        read -p "Restart SSH now? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            systemctl restart sshd
            echo -e "${GREEN}✅ SSH restarted on port $NEW_SSH_PORT${NC}"
            echo ""
            echo -e "${RED}🚨 TEST NOW from another terminal:${NC}"
            echo "   ssh -p $NEW_SSH_PORT clawdbot@$(hostname -I | awk '{print $1}')"
            echo ""
            echo "   If it works, you can remove the old port from UFW:"
            echo "   sudo ufw delete allow $CURRENT_SSH_PORT/tcp"
        else
            echo "  Skipped restart. Changes saved but not active."
            echo "  Run: sudo systemctl restart sshd"
        fi
    else
        echo -e "${RED}  ❌ SSH config test failed! Restoring backup...${NC}"
        cp "$BACKUP" "$SSHD_CONFIG"
    fi
fi

# ============================================
# STEP 3: fail2ban
# ============================================
echo ""
echo -e "${YELLOW}[3/4] fail2ban${NC}"

if ! command -v fail2ban-client &>/dev/null; then
    echo "Installing fail2ban..."
    apt-get install -y fail2ban
fi

# Configure fail2ban for SSH
cat > /etc/fail2ban/jail.local << EOF
[sshd]
enabled = true
port = $NEW_SSH_PORT
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600
EOF

systemctl enable fail2ban
systemctl restart fail2ban
echo -e "${GREEN}✅ fail2ban enabled (3 attempts → 1h ban)${NC}"

# ============================================
# STEP 4: Tailscale (guide only)
# ============================================
echo ""
echo -e "${YELLOW}[4/4] Tailscale${NC}"

if command -v tailscale &>/dev/null; then
    echo -e "${GREEN}✅ Already installed${NC}"
    tailscale status 2>/dev/null | head -3
else
    echo "Tailscale is recommended for secure remote access."
    echo ""
    read -p "Install Tailscale now? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        curl -fsSL https://tailscale.com/install.sh | sh
        echo ""
        echo "Run: sudo tailscale up"
        echo "Then configure OpenClaw gateway:"
        echo '  gateway.bind: "loopback"'
        echo '  gateway.tailscale.mode: "serve"'
    else
        echo "  Skipped. Install later: curl -fsSL https://tailscale.com/install.sh | sh"
    fi
fi

# ============================================
# DONE
# ============================================
echo ""
echo "=========================================="
echo -e "${GREEN}🔒 Hardening complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Test SSH from another terminal BEFORE closing this one"
echo "  2. Set up Tailscale for Gateway access"
echo "  3. Configure Gateway auth token in openclaw.json"
echo "  4. Run 'bash audit.sh' to verify"
echo ""
echo -e "${RED}⚠️  DO NOT close this terminal until you've confirmed SSH works!${NC}"
