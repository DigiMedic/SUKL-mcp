#!/bin/bash
# Validační script pro SÚKL MCP Server deployment
# Verze: 3.1.0

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Helper functions
print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

print_test() {
    echo -n "Testing: $1 ... "
}

print_pass() {
    echo -e "${GREEN}✓ PASS${NC}"
    PASSED=$((PASSED+1))
}

print_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    FAILED=$((FAILED+1))
}

print_skip() {
    echo -e "${YELLOW}⊘ SKIP${NC}: $1"
}

# Change to script directory
cd "$(dirname "$0")"

print_header "SÚKL MCP Server v3.1.0 - Deployment Validation"

# 1. Version consistency
print_header "1. Version Consistency"

print_test "pyproject.toml version"
if grep -q 'version = "3.1.0"' pyproject.toml; then
    print_pass
else
    print_fail "Version not 3.1.0 in pyproject.toml"
fi

print_test "__init__.py version"
if grep -q '__version__ = "3.1.0"' src/sukl_mcp/__init__.py; then
    print_pass
else
    print_fail "Version not 3.1.0 in __init__.py"
fi

print_test "fastmcp.yaml version"
if grep -q 'version: 3.1.0' fastmcp.yaml; then
    print_pass
else
    print_fail "Version not 3.1.0 in fastmcp.yaml"
fi

print_test "smithery.yaml version"
if grep -q 'version: "3.1.0"' smithery.yaml; then
    print_pass
else
    print_fail "Version not 3.1.0 in smithery.yaml"
fi

print_test "Dockerfile version"
if grep -q 'LABEL version="3.1.0"' Dockerfile; then
    print_pass
else
    print_fail "Version not 3.1.0 in Dockerfile"
fi

# 2. File existence
print_header "2. Required Files"

FILES=(
    "pyproject.toml"
    "README.md"
    "docs/deployment.md"
    "fastmcp.yaml"
    "smithery.yaml"
    "Dockerfile"
    ".dockerignore"
    "src/sukl_mcp/__init__.py"
    "src/sukl_mcp/__main__.py"
    "src/sukl_mcp/server.py"
    "src/sukl_mcp/client_csv.py"
    "src/sukl_mcp/models.py"
    "src/sukl_mcp/exceptions.py"
)

for file in "${FILES[@]}"; do
    print_test "File: $file"
    if [ -f "$file" ]; then
        print_pass
    else
        print_fail "File not found: $file"
    fi
done

# 3. YAML syntax validation
print_header "3. YAML Syntax Validation"

print_test "fastmcp.yaml syntax"
if python3 -c "import yaml; yaml.safe_load(open('fastmcp.yaml'))" 2>/dev/null; then
    print_pass
else
    print_fail "fastmcp.yaml syntax error"
fi

print_test "smithery.yaml syntax"
if python3 -c "import yaml; yaml.safe_load(open('smithery.yaml'))" 2>/dev/null; then
    print_pass
else
    print_fail "smithery.yaml syntax error"
fi

# 4. Python imports
print_header "4. Python Import Validation"

print_test "sukl_mcp.server import"
if python3 -c "from sukl_mcp.server import mcp" 2>/dev/null; then
    print_pass
else
    print_fail "Cannot import sukl_mcp.server"
fi

print_test "sukl_mcp.__version__ import"
if python3 -c "from sukl_mcp import __version__; assert __version__ == '3.1.0'" 2>/dev/null; then
    print_pass
else
    print_fail "Version mismatch in __version__"
fi

print_test "sukl_mcp.client_csv import"
if python3 -c "from sukl_mcp.client_csv import SUKLClient" 2>/dev/null; then
    print_pass
else
    print_fail "Cannot import SUKLClient"
fi

print_test "sukl_mcp.exceptions import"
if python3 -c "from sukl_mcp.exceptions import SUKLException" 2>/dev/null; then
    print_pass
else
    print_fail "Cannot import exceptions"
fi

# 5. Docker validation (optional)
print_header "5. Docker Validation (Optional)"

if command -v docker &> /dev/null; then
    print_test "Docker installation"
    print_pass

    print_test "Dockerfile exists"
    if [ -f "Dockerfile" ]; then
        print_pass
    else
        print_fail "Dockerfile not found"
    fi

    print_test ".dockerignore exists"
    if [ -f ".dockerignore" ]; then
        print_pass
    else
        print_fail ".dockerignore not found"
    fi
else
    print_skip "Docker not installed"
fi

# 6. FastMCP configuration
print_header "6. FastMCP Cloud Configuration"

print_test "fastmcp.yaml module path"
if grep -q "module: sukl_mcp.server" fastmcp.yaml; then
    print_pass
else
    print_fail "Module path not using absolute imports"
fi

print_test "fastmcp.yaml dependencies"
if grep -A 5 "dependencies:" fastmcp.yaml | grep -q "fastmcp" && \
   grep -A 5 "dependencies:" fastmcp.yaml | grep -q "pandas"; then
    print_pass
else
    print_fail "Missing dependencies in fastmcp.yaml"
fi

# 7. Smithery configuration
print_header "7. Smithery Configuration"

print_test "smithery.yaml runtime"
if grep -q 'runtime: "container"' smithery.yaml; then
    print_pass
else
    print_fail "Runtime not set to 'container'"
fi

print_test "smithery.yaml startCommand type"
if grep -q 'type: "http"' smithery.yaml; then
    print_pass
else
    print_fail "StartCommand type not set to 'http'"
fi

# 8. Documentation
print_header "8. Documentation"

print_test "README.md contains Smithery section"
if grep -q "Nasazení na Smithery" README.md; then
    print_pass
else
    print_fail "Smithery deployment section missing in README"
fi

print_test "docs/deployment.md contains Smithery reference"
if grep -q "Smithery" docs/deployment.md; then
    print_pass
else
    print_fail "Smithery reference missing in docs/deployment.md"
fi

print_test "CHANGELOG.md contains v3.1.0"
if grep -q "\[3.1.0\]" ../CHANGELOG.md 2>/dev/null || grep -q "\[3.1.0\]" CHANGELOG.md 2>/dev/null; then
    print_pass
else
    print_fail "Version 3.1.0 not documented in CHANGELOG"
fi

# Summary
print_header "Summary"
echo ""
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All validations passed! Ready for deployment.${NC}"
    echo ""
    echo "Next steps:"
    echo "  FastMCP Cloud: fastmcp deploy"
    echo "  Smithery:      smithery deploy"
    exit 0
else
    echo -e "${RED}❌ Some validations failed. Please fix the issues above.${NC}"
    echo ""
    echo "See DEPLOYMENT_CHECKLIST.md for detailed instructions."
    exit 1
fi
