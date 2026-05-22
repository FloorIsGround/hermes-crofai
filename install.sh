#!/usr/bin/env bash
set -euo pipefail

REPO="https://raw.githubusercontent.com/FloorIsGround/hermes-crofai/main"
INSTALL_DIR="${HERMES_HOME:-$HOME/.hermes}/plugins/model-providers/crofai"

echo "Installing CrofAI provider for Hermes Agent..."
mkdir -p "$INSTALL_DIR"

echo " Downloading plugin.yaml..."
curl -fsSL "$REPO/plugin.yaml" -o "$INSTALL_DIR/plugin.yaml"

echo " Downloading __init__.py..."
curl -fsSL "$REPO/__init__.py" -o "$INSTALL_DIR/__init__.py"

echo ""
echo " Installed to: $INSTALL_DIR"
echo ""
echo "Next steps:"
echo "  1. Add your CrofAI API key to ~/.hermes/.env:"
echo "     CROFAI_API_KEY=\"your-key-here\""
echo ""
echo "  2. Restart Hermes and select the provider:"
echo "     hermes --provider crofai"
echo "     # or: hermes model  (pick CrofAI from the list)"
echo ""
echo "  3. Or set it as your default provider:"
echo "     hermes config set model.provider crofai"
echo "     hermes config set model.default deepseek-v4-flash"
