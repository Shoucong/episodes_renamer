#!/bin/bash
# ===============================================================================
# Build Script for Episode Renamer Apps
# Usage: ./scripts/build.sh [app|llm|all|package]
# Run from project root directory
# ===============================================================================

set -e  # Exit on error

# Get project root (parent of scripts directory)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONDA_ENV="episode_renamer"

echo "🔨 Episode Renamer Build Script"
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

create_dmg() {
    local app_name="$1"
    local dmg_name="$2"
    
    echo ""
    echo "💿 Creating DMG for $app_name..."
    
    cd "$PROJECT_DIR/dist"
    
    # Create temp folder with app and Applications symlink
    rm -rf dmg_temp
    mkdir -p dmg_temp
    cp -R "$app_name" dmg_temp/
    ln -s /Applications dmg_temp/Applications
    
    # Create compressed DMG
    rm -f "$dmg_name"
    hdiutil create -volname "${app_name%.app}" \
        -srcfolder dmg_temp \
        -ov -format UDZO \
        "$dmg_name"
    
    # Cleanup
    rm -rf dmg_temp
    
    echo "✅ Created: dist/$dmg_name"
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
    package)
        # Build both apps first
        build_app "Episode Renamer" "app.spec" "Episode Renamer.app"
        build_app "Episode Renamer LLM" "app_llm.spec" "Episode Renamer LLM.app"
        
        # Create DMGs
        create_dmg "Episode Renamer.app" "Episode_Renamer.dmg"
        create_dmg "Episode Renamer LLM.app" "Episode_Renamer_LLM.dmg"
        
        echo ""
        echo "📦 DMG files ready for distribution:"
        ls -lh "$PROJECT_DIR/dist/"*.dmg
        ;;
    dmg)
        # Create DMGs only (assumes apps already built)
        create_dmg "Episode Renamer.app" "Episode_Renamer.dmg"
        create_dmg "Episode Renamer LLM.app" "Episode_Renamer_LLM.dmg"
        
        echo ""
        echo "📦 DMG files ready:"
        ls -lh "$PROJECT_DIR/dist/"*.dmg
        ;;
    *)
        echo "Usage: $0 [app|llm|all|package|dmg]"
        echo ""
        echo "Commands:"
        echo "  app      Build regular app only"
        echo "  llm      Build LLM app only"
        echo "  all      Build both apps (default)"
        echo "  package  Build both apps + create DMGs"
        echo "  dmg      Create DMGs only (apps must exist)"
        exit 1
        ;;
esac

echo ""
echo "🎉 Done! Output: $PROJECT_DIR/dist/"
