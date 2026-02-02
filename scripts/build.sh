#!/bin/bash
# ===============================================================================
# Build Script for Episode Renamer Apps
# Usage: ./scripts/build.sh [app|llm|all]
# Run from project root directory
# ===============================================================================

set -e  # Exit on error

# Get project root (parent of scripts directory)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONDA_ENV="episode_renamer"

echo "🔨 Building Episode Renamer Apps..."
echo "   Project: $PROJECT_DIR"

build_app() {
    local name="$1"
    local spec="$2"
    local app_name="$3"
    
    echo ""
    echo "📦 Building $name..."
    cd "$PROJECT_DIR"
    conda run -n "$CONDA_ENV" pyinstaller "build/specs/$spec" --noconfirm --distpath dist --workpath build/temp
    
    # Clear quarantine attribute (removes "banned" icon on macOS)
    echo "🔓 Clearing quarantine for $app_name..."
    xattr -cr "$PROJECT_DIR/dist/$app_name"
    
    echo "✅ $name built successfully!"
}

case "${1:-all}" in
    app)
        build_app "Episode Renamer" "app.spec" "Episode Renamer.app"
        ;;
    llm)
        build_app "Episode Renamer LLM" "app_llm.spec" "Episode Renamer LLM.app"
        ;;
    all)
        build_app "Episode Renamer" "app.spec" "Episode Renamer.app"
        build_app "Episode Renamer LLM" "app_llm.spec" "Episode Renamer LLM.app"
        ;;
    *)
        echo "Usage: $0 [app|llm|all]"
        exit 1
        ;;
esac

echo ""
echo "🎉 Build complete! Apps are in: $PROJECT_DIR/dist/"
