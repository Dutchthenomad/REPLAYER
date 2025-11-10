#!/bin/bash
# Setup Playwright MCP Server for Claude Desktop
# Usage: ./setup_playwright_mcp.sh

set -e

CONFIG_DIR="$HOME/.config/Claude"
CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"

echo "🔧 Setting up Playwright MCP Server..."

# Create config directory if it doesn't exist
mkdir -p "$CONFIG_DIR"

# Backup existing config if it exists
if [ -f "$CONFIG_FILE" ]; then
    echo "📋 Backing up existing config to ${CONFIG_FILE}.backup"
    cp "$CONFIG_FILE" "${CONFIG_FILE}.backup"
fi

# Check if jq is available for proper JSON manipulation
if command -v jq &> /dev/null; then
    echo "✅ Using jq for JSON manipulation"

    # If config exists and has content, merge; otherwise create new
    if [ -f "$CONFIG_FILE" ] && [ -s "$CONFIG_FILE" ]; then
        # Merge with existing config
        jq '.mcpServers.playwright = {
            "command": "npx",
            "args": ["-y", "@executeautomation/playwright-mcp-server"]
        }' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp"
        mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    else
        # Create new config
        jq -n '{
            "mcpServers": {
                "playwright": {
                    "command": "npx",
                    "args": ["-y", "@executeautomation/playwright-mcp-server"]
                }
            }
        }' > "$CONFIG_FILE"
    fi
else
    echo "⚠️  jq not found, using manual JSON creation"

    # Create simple config (overwrites existing - safer without jq)
    cat > "$CONFIG_FILE" << 'JSON_EOF'
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@executeautomation/playwright-mcp-server"]
    }
  }
}
JSON_EOF
fi

echo ""
echo "✅ Playwright MCP Server configured successfully!"
echo ""
echo "📄 Config location: $CONFIG_FILE"
echo ""
echo "📝 Configuration:"
cat "$CONFIG_FILE"
echo ""
echo "🔄 Next steps:"
echo "   1. Restart Claude Desktop to load the MCP server"
echo "   2. Verify tools are available in the next session"
echo ""
echo "🎯 Available tools after restart:"
echo "   - mcp__playwright__navigate"
echo "   - mcp__playwright__screenshot"
echo "   - mcp__playwright__click"
echo "   - mcp__playwright__fill"
echo "   - mcp__playwright__console"
echo ""
