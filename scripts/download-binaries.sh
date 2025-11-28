#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Harmonix SE: Binary Download Script ===${NC}"
echo -e "${BLUE}This script downloads portable Python runtime and FFmpeg binaries${NC}"
echo ""

# Base directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BINARIES_DIR="$PROJECT_ROOT/src-tauri/binaries"

mkdir -p "$BINARIES_DIR"

# Detect current platform
PLATFORM=$(uname -s)
ARCH=$(uname -m)

echo "Detected platform: $PLATFORM ($ARCH)"
echo ""

# Python version to download (use 3.11 for stability)
PYTHON_VERSION="3.11"
PYTHON_VERSION_FULL="3.11.14"
# python-build-standalone release tag
PBS_TAG="20251120"

# Function to download and extract Python portable build
download_python() {
    local target=$1
    local url=$2
    local output_dir="$BINARIES_DIR/python-${target}"
    
    echo -e "${YELLOW}Downloading Python ${PYTHON_VERSION} for ${target}...${NC}"
    
    if [ -d "$output_dir" ]; then
        echo "  Python already exists at $output_dir, skipping..."
        return
    fi
    
    # Download to temp directory
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    echo "  Downloading from: $url"
    curl -L -o python.tar.gz "$url"
    
    # Extract
    echo "  Extracting..."
    tar -xzf python.tar.gz
    
    # Move to binaries directory
    mv python "$output_dir"
    chmod +x "$output_dir/bin/python3" 2>/dev/null || true
    chmod +x "$output_dir/bin/python" 2>/dev/null || true
    chmod +x "$output_dir/python.exe" 2>/dev/null || true
    
    # Cleanup
    cd - > /dev/null
    rm -rf "$TEMP_DIR"
    
    echo -e "${GREEN}✓ Python downloaded: python-${target}${NC}"
}

# Function to download and extract FFmpeg
download_ffmpeg_macos() {
    local target=$1
    local output_name="ffmpeg-${target}"
    
    echo -e "${YELLOW}Downloading FFmpeg for macOS (${target})...${NC}"
    
    if [ -f "$BINARIES_DIR/$output_name" ]; then
        echo "  FFmpeg already exists, skipping..."
        return
    fi
    
    # Use official FFmpeg static builds
    FFMPEG_URL="https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"
    
    # Download to temp directory
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    echo "  Downloading from: $FFMPEG_URL"
    curl -L -o ffmpeg.zip "$FFMPEG_URL"
    
    # Extract
    unzip -q ffmpeg.zip
    
    # Copy to binaries directory with target-triple naming
    cp ffmpeg "$BINARIES_DIR/$output_name"
    chmod +x "$BINARIES_DIR/$output_name"
    
    # Cleanup
    cd - > /dev/null
    rm -rf "$TEMP_DIR"
    
    echo -e "${GREEN}✓ FFmpeg downloaded: $output_name${NC}"
}

download_ffmpeg_windows() {
    local target=$1
    local output_name="ffmpeg-${target}.exe"
    
    echo -e "${YELLOW}Downloading FFmpeg for Windows (${target})...${NC}"
    
    if [ -f "$BINARIES_DIR/$output_name" ]; then
        echo "  FFmpeg already exists, skipping..."
        return
    fi
    
    # Use FFmpeg Windows builds from gyan.dev
    FFMPEG_URL="https://github.com/GyanD/codexffmpeg/releases/download/7.1/ffmpeg-7.1-essentials_build.zip"
    
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    echo "  Downloading from: $FFMPEG_URL"
    curl -L -o ffmpeg.zip "$FFMPEG_URL"
    
    unzip -q ffmpeg.zip
    
    # Find and copy the ffmpeg.exe
    find . -name "ffmpeg.exe" -exec cp {} "$BINARIES_DIR/$output_name" \;
    
    cd - > /dev/null
    rm -rf "$TEMP_DIR"
    
    echo -e "${GREEN}✓ FFmpeg downloaded: $output_name${NC}"
}

# Main download logic
if [[ "$PLATFORM" == "Darwin" ]]; then
    echo -e "${BLUE}=== Downloading for macOS ===${NC}"
    echo ""
    
    # Check if we're in CI mode with a specific target
    if [ -n "$TARGET_ARCH" ]; then
        echo "CI mode detected: downloading for $TARGET_ARCH"
        
        if [ "$TARGET_ARCH" == "universal-apple-darwin" ]; then
            # Universal binary needs both architectures
            echo "Universal build detected: downloading both arm64 and x86_64"
            download_python "aarch64-apple-darwin" \
                "https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PYTHON_VERSION_FULL}+${PBS_TAG}-aarch64-apple-darwin-install_only.tar.gz"
            
            download_python "x86_64-apple-darwin" \
                "https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PYTHON_VERSION_FULL}+${PBS_TAG}-x86_64-apple-darwin-install_only.tar.gz"
            
            download_ffmpeg_macos "aarch64-apple-darwin"
            download_ffmpeg_macos "x86_64-apple-darwin"
        else
            # Single architecture
            download_python "$TARGET_ARCH" \
                "https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PYTHON_VERSION_FULL}+${PBS_TAG}-${TARGET_ARCH}-install_only.tar.gz"
            download_ffmpeg_macos "$TARGET_ARCH"
        fi
    else
        # Local development: download for both architectures
        download_python "aarch64-apple-darwin" \
            "https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PYTHON_VERSION_FULL}+${PBS_TAG}-aarch64-apple-darwin-install_only.tar.gz"
        
        download_python "x86_64-apple-darwin" \
            "https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PYTHON_VERSION_FULL}+${PBS_TAG}-x86_64-apple-darwin-install_only.tar.gz"
        
        # Download FFmpeg for both architectures
        download_ffmpeg_macos "aarch64-apple-darwin"
        download_ffmpeg_macos "x86_64-apple-darwin"
        
        echo ""
        echo -e "${BLUE}=== Downloading Windows binaries (for cross-platform support) ===${NC}"
        echo ""
        
        # Also download Windows binaries for future cross-compilation
        download_python "x86_64-pc-windows-msvc" \
            "https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PYTHON_VERSION_FULL}+${PBS_TAG}-x86_64-pc-windows-msvc-install_only.tar.gz"
        
        download_ffmpeg_windows "x86_64-pc-windows-msvc"
    fi
    
elif [[ "$PLATFORM" == "Linux" ]]; then
    echo -e "${BLUE}=== Downloading for Linux ===${NC}"
    echo ""
    
    # Download Python for x86_64
    download_python "x86_64-unknown-linux-gnu" \
        "https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PYTHON_VERSION_FULL}+${PBS_TAG}-x86_64-unknown-linux-gnu-install_only.tar.gz"
    
    # Download FFmpeg for Linux
    echo -e "${YELLOW}Downloading FFmpeg for Linux (x86_64)...${NC}"
    
    FFMPEG_LINUX="ffmpeg-x86_64-unknown-linux-gnu"
    if [ ! -f "$BINARIES_DIR/$FFMPEG_LINUX" ]; then
        # Use static FFmpeg build from johnvansickle
        FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        
        TEMP_DIR=$(mktemp -d)
        cd "$TEMP_DIR"
        
        echo "  Downloading from: $FFMPEG_URL"
        curl -L -o ffmpeg.tar.xz "$FFMPEG_URL"
        
        tar -xf ffmpeg.tar.xz
        
        # Find and copy ffmpeg binary
        find . -name "ffmpeg" -type f -executable -exec cp {} "$BINARIES_DIR/$FFMPEG_LINUX" \;
        chmod +x "$BINARIES_DIR/$FFMPEG_LINUX"
        
        cd - > /dev/null
        rm -rf "$TEMP_DIR"
        
        echo -e "${GREEN}✓ FFmpeg downloaded: $FFMPEG_LINUX${NC}"
    else
        echo "  FFmpeg already exists, skipping..."
    fi
    
elif [[ "$PLATFORM" == "MINGW"* ]] || [[ "$PLATFORM" == "MSYS"* ]]; then
    echo -e "${BLUE}=== Downloading for Windows ===${NC}"
    echo ""
    
    download_python "x86_64-pc-windows-msvc" \
        "https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PYTHON_VERSION_FULL}+${PBS_TAG}-x86_64-pc-windows-msvc-install_only.tar.gz"
    
    download_ffmpeg_windows "x86_64-pc-windows-msvc"
    
else
    echo "Unsupported platform: $PLATFORM"
    exit 1
fi

echo ""
echo -e "${GREEN}=== ✓ All binaries downloaded ===${NC}"
echo "Binaries location: $BINARIES_DIR"
echo ""
echo "Downloaded:"
du -sh "$BINARIES_DIR"/* 2>/dev/null || ls -lh "$BINARIES_DIR"

echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Install Python dependencies in bundled Python:"
echo "   cd $PROJECT_ROOT"
echo "   For macOS arm64: ./src-tauri/binaries/python-aarch64-apple-darwin/bin/pip3 install -r requirements.txt"
echo "2. Run 'npm run tauri build' to create production bundle"
