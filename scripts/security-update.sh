#!/bin/bash

# OriginMark Security Update Script
# This script updates all dependencies to their latest secure versions

set -e  # Exit on any error

echo "🔒 OriginMark Security Update Script"
echo "====================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}$1${NC}"
}

# Check if we're in the right directory
if [ ! -f "ROADMAP.md" ]; then
    print_error "Please run this script from the OriginMark root directory"
    exit 1
fi

print_header "📦 Updating Python Dependencies (API)"
echo "----------------------------------------"

if [ -f "api/requirements.txt" ]; then
    cd api
    
    # Create backup
    cp requirements.txt requirements.txt.backup
    print_status "Created backup: requirements.txt.backup"
    
    # Check for outdated packages
    print_status "Checking for outdated Python packages..."
    pip list --outdated || true
    
    # Update pip itself
    print_status "Updating pip..."
    python -m pip install --upgrade pip
    
    # Install/update dependencies
    print_status "Installing updated dependencies..."
    pip install -r requirements.txt --upgrade
    
    # Security scan
    if command -v safety &> /dev/null; then
        print_status "Running security scan with Safety..."
        safety check
    else
        print_warning "Safety not installed. Install with: pip install safety"
    fi
    
    # Static analysis
    if command -v bandit &> /dev/null; then
        print_status "Running security analysis with Bandit..."
        bandit -r . -f json -o ../security-reports/bandit-api.json || true
        bandit -r . || true
    else
        print_warning "Bandit not installed. Install with: pip install bandit"
    fi
    
    cd ..
else
    print_warning "api/requirements.txt not found"
fi

print_header "🌐 Updating Node.js Dependencies (Web Dashboard)"
echo "------------------------------------------------"

if [ -f "web/package.json" ]; then
    cd web
    
    # Check Node.js version
    node_version=$(node --version)
    print_status "Current Node.js version: $node_version"
    
    # Check for outdated packages
    print_status "Checking for outdated npm packages..."
    npm outdated || true
    
    # Update dependencies
    print_status "Updating npm dependencies..."
    npm update
    
    # Security audit
    print_status "Running npm security audit..."
    npm audit
    
    # Fix vulnerabilities
    print_status "Attempting to fix vulnerabilities..."
    npm audit fix
    
    # Check again
    npm audit --audit-level high || print_warning "High-severity vulnerabilities found"
    
    cd ..
else
    print_warning "web/package.json not found"
fi

print_header "⛓️ Updating Blockchain Dependencies"
echo "-----------------------------------"

if [ -f "blockchain/package.json" ]; then
    cd blockchain
    
    # Check for outdated packages
    print_status "Checking for outdated blockchain packages..."
    npm outdated || true
    
    # Update dependencies
    print_status "Updating blockchain dependencies..."
    npm update
    
    # Security audit
    print_status "Running npm security audit for blockchain..."
    npm audit
    npm audit fix
    
    # Compile contracts to check for issues
    print_status "Compiling smart contracts..."
    npx hardhat compile
    
    cd ..
else
    print_warning "blockchain/package.json not found"
fi

print_header "📚 Updating SDK Dependencies"
echo "-----------------------------"

# TypeScript SDK
if [ -f "sdk/ts-sdk/package.json" ]; then
    cd sdk/ts-sdk
    
    print_status "Updating TypeScript SDK dependencies..."
    npm outdated || true
    npm update
    npm audit
    npm audit fix
    
    # Build to check for issues
    print_status "Building TypeScript SDK..."
    npm run build
    
    cd ../..
fi

# Web3 SDK
if [ -f "sdk/web3-sdk/package.json" ]; then
    cd sdk/web3-sdk
    
    print_status "Updating Web3 SDK dependencies..."
    npm outdated || true
    npm update
    npm audit
    npm audit fix
    
    # Build to check for issues
    print_status "Building Web3 SDK..."
    npm run build
    
    cd ../..
fi

# Python CLI
if [ -f "sdk/py-cli/setup.py" ]; then
    cd sdk/py-cli
    
    print_status "Updating Python CLI dependencies..."
    pip install -e . --upgrade
    
    cd ../..
fi

print_header "🔍 Security Scanning"
echo "--------------------"

# Create security reports directory
mkdir -p security-reports

# Check for known vulnerabilities
if command -v snyk &> /dev/null; then
    print_status "Running Snyk security scan..."
    snyk test --json > security-reports/snyk-report.json || true
    snyk test || print_warning "Snyk found vulnerabilities"
else
    print_warning "Snyk CLI not installed. Install with: npm install -g snyk"
fi

# Generate dependency tree
print_status "Generating dependency trees..."
if [ -f "web/package.json" ]; then
    cd web
    npm ls --depth=0 > ../security-reports/npm-dependencies.txt 2>&1 || true
    cd ..
fi

if [ -f "api/requirements.txt" ]; then
    cd api
    pip freeze > ../security-reports/pip-dependencies.txt
    cd ..
fi

print_header "📊 Security Report Summary"
echo "---------------------------"

print_status "Security scan completed!"
print_status "Reports saved in: security-reports/"

if [ -f "security-reports/snyk-report.json" ]; then
    vulnerabilities=$(jq '.vulnerabilities | length' security-reports/snyk-report.json 2>/dev/null || echo "N/A")
    print_status "Snyk vulnerabilities found: $vulnerabilities"
fi

print_header "🔧 Post-Update Tasks"
echo "--------------------"

echo "Manual tasks to complete:"
echo "1. Review security-reports/ directory"
echo "2. Test application functionality"
echo "3. Update environment variables if needed"
echo "4. Review and update .env files"
echo "5. Test browser extensions"
echo "6. Verify WordPress plugin compatibility"
echo "7. Run full test suite"

print_header "🚀 Recommended Next Steps"
echo "-------------------------"

echo "1. Run the test suite:"
echo "   cd api && python -m pytest"
echo "   cd web && npm test"
echo "   cd blockchain && npx hardhat test"

echo ""
echo "2. Check for critical security advisories:"
echo "   - https://github.com/advisories"
echo "   - https://nvd.nist.gov/"
echo "   - https://security.snyk.io/"

echo ""
echo "3. Review changelog for breaking changes:"
echo "   - Check dependency changelogs"
echo "   - Test all critical functionality"
echo "   - Update documentation if needed"

print_status "Security update process completed! ✅"

# Exit with appropriate code
if [ -f "security-reports/snyk-report.json" ]; then
    vulnerabilities=$(jq '.vulnerabilities | length' security-reports/snyk-report.json 2>/dev/null || echo "0")
    if [ "$vulnerabilities" != "0" ] && [ "$vulnerabilities" != "N/A" ]; then
        print_warning "Vulnerabilities detected. Please review the security reports."
        exit 1
    fi
fi

exit 0 