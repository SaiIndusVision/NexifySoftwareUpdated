#!/bin/bash

echo "Building NexifyTool Desktop Application..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    print_error "package.json not found. Make sure you're in the NexifySoftware directory."
    exit 1
fi

if [ ! -d "src" ]; then
    print_error "src directory not found. Make sure the project is set up correctly."
    exit 1
fi

if [ ! -f "src/main.js" ]; then
    print_error "src/main.js not found. Please ensure src/main.js exists in the project directory."
    exit 1
fi

if [ ! -f "src/loading.html" ]; then
    print_status "Creating src/loading.html..."
    echo '<!DOCTYPE html><html><body><h1>Loading NexifyTool...</h1><style>body{font-family:Arial,sans-serif;background:#2B1055;color:#fff;text-align:center;padding-top:100px;}h1{font-size:36px;}</style></body></html>' > src/loading.html
fi

if [ ! -f "src/error.html" ]; then
    print_status "Creating src/error.html..."
    echo '<!DOCTYPE html><html><body><h1>Error: Failed to start Django server</h1><p>Please check the console for details or contact support.</p><style>body{font-family:Arial,sans-serif;background:#2B1055;color:#fff;text-align:center;padding-top:100px;}h1{font-size:36px;}p{font-size:18px;}</style></body></html>' > src/error.html
fi

if [ ! -d "django-backend" ]; then
    print_error "django-backend directory not found. Make sure your Django project is copied to django-backend/"
    exit 1
fi

if [ ! -f "django-backend/manage.py" ]; then
    print_error "django-backend/manage.py not found. Make sure your Django project is set up correctly."
    exit 1
fi

if [ ! -d "nexify-env" ]; then
    print_status "Creating nexify-env virtual environment..."
    python3 -m venv nexify-env
fi

# Set up external configuration directory
CONFIG_DIR="$HOME/.nexify"
print_status "Setting up external configuration directory at $CONFIG_DIR..."
mkdir -p "$CONFIG_DIR"
mkdir -p "$CONFIG_DIR/media"

# Pre-create .requirements_installed flag
print_status "Pre-creating .requirements_installed flag..."
touch "$CONFIG_DIR/.requirements_installed"
if [ $? -eq 0 ]; then
    print_success ".requirements_installed flag created at $CONFIG_DIR"
else
    print_error "Failed to create .requirements_installed flag"
    exit 1
fi

# Install Python dependencies
print_status "Installing Python dependencies..."
source nexify-env/bin/activate
pip install -r django-backend/requirements.txt
if [ $? -ne 0 ]; then
    print_error "Failed to install Python dependencies."
    exit 1
fi
deactivate

# Collect static files
print_status "Collecting Django static files..."
source nexify-env/bin/activate
cd django-backend
../nexify-env/bin/python manage.py collectstatic --noinput
cd ..
deactivate

# Warn about default icons
print_status "Checking for icon files..."
if [ ! -f "assets/icon.png" ] || [ ! -f "assets/icon.ico" ]; then
    print_warning "Custom icons not found. Using default Electron icons. Add a 256x256 PNG at assets/icon.png and an ICO at assets/icon.ico for production."
fi

# Create cleanup script for AppImage
print_status "Checking for cleanup script..."
if [ ! -f "scripts/cleanup.sh" ]; then
    print_status "Creating scripts/cleanup.sh..."
    mkdir -p scripts
    cat << 'EOF' > scripts/cleanup.sh
#!/bin/bash
CONFIG_DIR="$HOME/.nexify"
LOG_FILE="$CONFIG_DIR/logs/uninstall.log"

echo "This script will delete all NexifyTool data in $CONFIG_DIR, including database and media files."
echo "This action cannot be undone. Continue? [y/N]"
read -r response
if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
    mkdir -p "$CONFIG_DIR/logs"
    echo "$(date '+%Y-%m-%d %H:%M:%S') Attempting to delete $CONFIG_DIR" >> "$LOG_FILE"
    rm -rf "$CONFIG_DIR" && {
        echo "$(date '+%Y-%m-%d %H:%M:%S') Successfully deleted $CONFIG_DIR" >> "$LOG_FILE"
        echo "Data deleted successfully."
    } || {
        echo "$(date '+%Y-%m-%d %H:%M:%S') Failed to delete $CONFIG_DIR" >> "$LOG_FILE"
        echo "Failed to delete $CONFIG_DIR. Please delete it manually."
    }
else
    echo "Cleanup aborted."
fi
EOF
    chmod +x scripts/cleanup.sh
fi

# Clean previous builds
print_status "Cleaning previous builds..."
rm -rf dist/
rm -rf build/*.yaml
rm -rf build/debian
rm -rf build/nsis

# Clear electron-builder cache more thoroughly
print_status "Clearing electron-builder cache..."
rm -rf ~/.cache/electron-builder/
rm -rf node_modules/.cache/
# Windows cache cleanup (if on Windows)
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    rm -rf "$LOCALAPPDATA/electron-builder/Cache/" 2>/dev/null || true
fi

# Install/update dependencies
print_status "Installing Node.js dependencies..."
npm install
if [ $? -ne 0 ]; then
    print_error "Failed to install Node.js dependencies."
    exit 1
fi

# Function to build for specific platform
build_platform() {
    local platform=$1
    local command=$2
    
    print_status "Building for $platform..."
    
    if [ "$platform" = "Linux" ]; then
        # Create Debian postrm script
        print_status "Creating Debian postrm script..."
        mkdir -p build/debian
        cat << 'EOF' > build/debian/postrm
#!/bin/sh
set -e

CONFIG_DIR="$HOME/.nexify"
LOG_FILE="$CONFIG_DIR/logs/uninstall.log"

mkdir -p "$CONFIG_DIR/logs"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

if [ "$1" = "purge" ]; then
    if command -v zenity >/dev/null 2>&1; then
        if zenity --question --title="NexifyTool Uninstallation" --text="Do you want to delete all application data, including database and media files in $CONFIG_DIR? This action cannot be undone."; then
            log "Attempting to delete $CONFIG_DIR"
            rm -rf "$CONFIG_DIR" && log "Successfully deleted $CONFIG_DIR" || {
                log "Failed to delete $CONFIG_DIR"
                zenity --error --title="NexifyTool Uninstallation" --text="Failed to delete $CONFIG_DIR. Please delete it manually."
            }
        else
            log "User chose not to delete $CONFIG_DIR"
        fi
    else
        echo "Do you want to delete all application data, including database and media files in $CONFIG_DIR? This action cannot be undone. [y/N]"
        read -r response
        if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
            log "Attempting to delete $CONFIG_DIR"
            rm -rf "$CONFIG_DIR" && log "Successfully deleted $CONFIG_DIR" || {
                log "Failed to delete $CONFIG_DIR"
                echo "Failed to delete $CONFIG_DIR. Please delete it manually."
            }
        else
            log "User chose not to delete $CONFIG_DIR"
        fi
    fi
fi

exit 0
EOF
        chmod +x build/debian/postrm
        npm run "$command" -- --linux deb -c.extraMetadata.scripts.postrm=build/debian/postrm
        npm run "$command" -- --linux AppImage
    else
        # Simplified Windows build without custom NSIS script for now
        print_status "Building Windows version (simplified)..."
        npm run "$command"
    fi
    
    if [ $? -eq 0 ]; then
        print_success "$platform build completed successfully!"
        
        if [ -d "dist" ]; then
            print_status "Generated files for $platform:"
            ls -la dist/ | grep -E "\.(exe|deb|AppImage|dmg)$" || echo "No installer files found."
        fi
    else
        print_error "$platform build failed!"
        exit 1
    fi
}

# Build based on argument or build all
case "${1:-all}" in
    "windows" | "win")
        build_platform "Windows" "build-win"
        ;;
    "linux")
        build_platform "Linux" "build-linux"
        ;;
    "all")
        print_status "Building for all supported platforms..."
        echo ""
        
        build_platform "Linux" "build-linux"
        echo ""
        
        build_platform "Windows" "build-win"
        echo ""
        
        print_success "All builds completed!"
        ;;
    *)
        print_error "Invalid platform. Use: windows, linux, or all"
        exit 1
        ;;
esac

echo ""
print_status "Build Summary:"
echo "==============="

if [ -d "dist" ]; then
    print_status "Generated files:"
    ls -la dist/
    echo ""
    
    exe_files=$(find dist/ -name "*.exe" 2>/dev/null)
    deb_files=$(find dist/ -name "*.deb" 2>/dev/null)
    appimage_files=$(find dist/ -name "*.AppImage" 2>/dev/null)
    
    if [ ! -z "$exe_files" ]; then
        print_success "Windows Installer(s):"
        echo "$exe_files"
        echo "Uninstallation: Use Control Panel > Programs and Features. To delete data, use the dashboard's 'Clear All Data' feature or manually remove %USERPROFILE%\\.nexify."
    fi
    
    if [ ! -z "$deb_files" ]; then
        print_success "Linux Package(s):"
        echo "$deb_files"
        echo "Uninstallation: Run 'sudo apt purge nexify-tool' to be prompted to delete ~/.nexify data."
    fi
    
    if [ ! -z "$appimage_files" ]; then
        print_success "Linux AppImage(s):"
        echo "$appimage_files"
        echo "Uninstallation: Delete the .AppImage file. To erase all data, run './scripts/cleanup.sh'."
    fi
    
    echo ""
    print_status "Installation Instructions:"
    echo "========================="
    
    if [ ! -z "$exe_files" ]; then
        echo "Windows: Double-click the .exe file to install"
        echo "         Database and media files will be stored in %USERPROFILE%\\.nexify"
        echo "         If you see a white screen, check the console logs (run with --enable-logging)"
    fi
    
    if [ ! -z "$deb_files" ]; then
        echo "Ubuntu/Debian: Install system dependencies first:"
        echo "               sudo apt-get install python3 python3-pip zenity"
        echo "               Then install: sudo dpkg -i <filename>.deb"
        echo "               sudo apt-get install -f  # if dependencies are missing"
        echo "               Run as a non-root user in a graphical environment"
        echo "               Database and media files will be stored in ~/.nexify"
    fi
    
    if [ ! -z "$appimage_files" ]; then
        echo "Linux AppImage: Install system dependencies first:"
        echo "                sudo apt-get install python3 python3-pip"
        echo "                Then run: chmod +x <filename>.AppImage && ./<filename>.AppImage"
        echo "                To uninstall, delete the .AppImage file."
        echo "                To erase all data, run: ./scripts/cleanup.sh (included in the AppImage directory)"
        echo "                Database and media files will be stored in ~/.nexify"
    fi
else
    print_error "No build output found in dist/ directory"
    exit 1
fi

echo ""
print_status "The application will automatically:"
echo "- Use external database at $CONFIG_DIR/db.sqlite3"
echo "- Use external media directory at $CONFIG_DIR/media"
echo "- Apply database migrations on first run or update"
echo "- Install Python dependencies on first run"
echo "- Start Django server on port 8000"
echo "- Open the application in an Electron window"
echo ""
print_success "Build process completed!"