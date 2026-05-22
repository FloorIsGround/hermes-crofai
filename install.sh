#!/usr/bin/env bash
set -euo pipefail

REPO="https://raw.githubusercontent.com/FloorIsGround/hermes-crofai/testing/crofai-widget"
INSTALL_DIR="${HERMES_HOME:-$HOME/.hermes}/plugins/model-providers/crofai"
WIDGET_DIR="${HERMES_HOME:-$HOME/.hermes}/plugins/crofai-widget"

echo "Installing CrofAI provider for Hermes Agent..."
mkdir -p "$INSTALL_DIR"

echo " Downloading plugin.yaml..."
curl -fsSL "$REPO/plugin.yaml" -o "$INSTALL_DIR/plugin.yaml"

echo " Downloading __init__.py..."
curl -fsSL "$REPO/__init__.py" -o "$INSTALL_DIR/__init__.py"

echo ""
echo "Installing CrofAI TUI widget companion plugin..."
mkdir -p "$WIDGET_DIR"

echo " Downloading crofai-widget/plugin.yaml..."
curl -fsSL "$REPO/crofai-widget/plugin.yaml" -o "$WIDGET_DIR/plugin.yaml"

echo " Downloading crofai-widget/__init__.py..."
curl -fsSL "$REPO/crofai-widget/__init__.py" -o "$WIDGET_DIR/__init__.py"

echo ""
echo " Installed to: $INSTALL_DIR"
echo " Widget plugin: $WIDGET_DIR"
echo ""
echo "Next steps:"
echo "  1. Add your CrofAI API key to ~/.hermes/.env:"
echo "     CROFAI_API_KEY=\"your-key-here\""
echo ""
echo "  2. Enable the widget plugin:"
echo "     hermes plugins enable crofai-widget"
echo ""
echo "  3. Restart Hermes and select the provider:"
echo "     hermes --provider crofai"
echo "     # or: hermes model  (pick CrofAI from the list)"
echo ""
echo "  4. Or set it as your default:"
echo "     hermes config set model.provider crofai"
echo "     hermes config set model.default deepseek-v4-flash"
echo ""
echo "  5. In the TUI, type /crofai to see usage stats."
