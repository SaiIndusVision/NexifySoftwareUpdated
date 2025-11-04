#!/bin/bash

echo "🔧 Installing Django Dependencies for NexifyTool..."

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

# Check if we're in the right directory
if [ ! -d "NexifyTool_Local" ]; then
    print_error "NexifyTool_Local directory not found. Make sure you're in the electron-app directory."
    exit 1
fi

# Navigate to Django project
cd NexifyTool_Local

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt not found in NexifyTool_Local directory."
    exit 1
fi

print_status "Found requirements.txt, installing dependencies..."
echo ""

# Show what will be installed
print_status "Dependencies to install:"
cat requirements.txt
echo ""

# Try different installation methods
install_success=false

# Method 1: pip3 install
print_status "Trying: pip3 install -r requirements.txt --user"
if pip3 install -r requirements.txt --user; then
    print_success "Dependencies installed successfully with pip3!"
    install_success=true
else
    print_warning "pip3 installation failed, trying alternative methods..."
fi

# Method 2: python3 -m pip install (if first method failed)
if [ "$install_success" = false ]; then
    print_status "Trying: python3 -m pip install -r requirements.txt --user"
    if python3 -m pip install -r requirements.txt --user; then
        print_success "Dependencies installed successfully with python3 -m pip!"
        install_success=true
    else
        print_warning "python3 -m pip installation failed..."
    fi
fi

# Method 3: Install specific missing packages (if still failed)
if [ "$install_success" = false ]; then
    print_status "Trying to install common missing packages individually..."
    
    # Common packages that might be missing
    packages=("fpdf" "django" "djangorestframework" "pillow" "requests" "python-decouple")
    
    for package in "${packages[@]}"; do
        print_status "Installing $package..."
        pip3 install "$package" --user 2>/dev/null || python3 -m pip install "$package" --user 2>/dev/null
    done
    
    print_warning "Individual package installation completed (some may have failed)"
fi

echo ""

# Test Django setup
print_status "Testing Django setup..."
cd ..

if python3 NexifyTool_Local/manage.py check --deploy 2>/dev/null; then
    print_success "Django setup looks good!"
elif python3 NexifyTool_Local/manage.py check 2>/dev/null; then
    print_success "Django basic setup is working!"
else
    print_warning "Django check failed, but continuing anyway..."
fi

echo ""
print_status "Dependency installation completed!"
echo ""
print_status "Now you can run:"
echo "  npm run dev"
echo ""
print_warning "If you still get import errors, you may need to:"
echo "1. Check if all packages in requirements.txt are correct"
echo "2. Install missing packages manually: pip3 install <package-name> --user"
echo "3. Consider using a virtual environment"

# Go back to original directory
cd ..