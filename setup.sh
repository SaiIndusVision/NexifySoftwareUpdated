#!/bin/bash

echo "🚀 Setting up NexifyTool Desktop Application..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    print_error "npm is not installed. Please install npm first."
    exit 1
fi

# Check if Python3 is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if pip3 is installed
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed. Please install pip3 first."
    exit 1
fi

print_status "All prerequisites found!"

# Create directory structure
print_status "Creating project structure..."

# Create the electron app structure
mkdir -p nexify-desktop-app/{src,assets,django-backend}

# Copy Django project to django-backend directory
print_status "Copying Django project..."
cp -r ./* nexify-desktop-app/django-backend/ 2>/dev/null || true
cp -r ./.* nexify-desktop-app/django-backend/ 2>/dev/null || true

# Remove the nexify-desktop-app directory from the copy (avoid recursion)
rm -rf nexify-desktop-app/django-backend/nexify-desktop-app

# Navigate to the new directory
cd nexify-desktop-app

# Create package.json (this will be replaced by the artifact content)
print_status "Creating package.json..."

# Create src directory files
print_status "Creating Electron main process..."

# Create assets directory and placeholder icon
print_status "Creating application assets..."
mkdir -p assets

# Create a simple PNG icon (placeholder)
cat > assets/icon.png << 'EOF'
# This is a placeholder. Replace with your actual icon.
# For now, we'll create a simple text-based icon
EOF

# Create ICO file for Windows (placeholder)
cp assets/icon.png assets/icon.ico 2>/dev/null || touch assets/icon.ico

# Initialize npm project
print_status "Initializing npm project..."
npm init -y

# Install dependencies
print_status "Installing Electron and build dependencies..."
npm install --save-dev electron electron-builder
npm install --save axios express

print_success "Project structure created successfully!"

print_status "Project structure:"
echo "nexify-desktop-app/"
echo "├── package.json          # Electron app configuration"
echo "├── src/"
echo "│   ├── main.js          # Electron main process"
echo "│   └── loading.html     # Loading page"
echo "├── assets/"
echo "│   ├── icon.png         # App icon (PNG)"
echo "│   └── icon.ico         # App icon (ICO)"
echo "├── django-backend/      # Your Django project"
echo "└── dist/               # Built applications (after build)"

echo ""
print_success "Setup completed!"
echo ""
print_status "Next steps:"
echo "1. cd nexify-desktop-app"
echo "2. Replace the package.json, src/main.js, and src/loading.html with the provided artifacts"
echo "3. Add your app icon to assets/icon.png and assets/icon.ico"
echo "4. Run 'npm run dev' to test in development mode"
echo "5. Run 'npm run build-all' to build for all platforms"
echo "6. Run 'npm run build-win' to build Windows .exe"
echo "7. Run 'npm run build-linux' to build Linux .deb"

echo ""
print_warning "Note: Make sure to install proper app icons in assets/ directory before building for distribution!"
echo ""
print_status "The built files will be available in the 'dist' folder after running build commands."