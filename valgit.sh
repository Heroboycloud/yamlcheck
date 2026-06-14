#!/bin/bash
# validate-github-action.sh

FILE="$1"

if [ -z "$FILE" ]; then
    echo "Usage: $0 <workflow-file.yml>"
    exit 1
fi

if [ ! -f "$FILE" ]; then
    echo "❌ File not found: $FILE"
    exit 1
fi

echo "🔍 Validating: $FILE"
echo "=================================="

# Check YAML syntax with yamllint if available
if command -v yamllint &> /dev/null; then
    echo "Running yamllint..."
    yamllint "$FILE"
    if [ $? -ne 0 ]; then
        echo "❌ YAML syntax errors found"
        exit 1
    fi
else
    echo "⚠️  yamllint not installed. Install with: pip install yamllint"
    # Basic check with Python
    python3 -c "import yaml; yaml.safe_load(open('$FILE'))" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "❌ Invalid YAML syntax"
        exit 1
    fi
fi

# Check required fields
echo "Checking required fields..."
if ! grep -q "^on:" "$FILE"; then
    echo "❌ Missing 'on:' field"
    exit 1
fi

if ! grep -q "^jobs:" "$FILE"; then
    echo "❌ Missing 'jobs:' field"
    exit 1
fi

if ! grep -q "runs-on:" "$FILE"; then
    echo "❌ Missing 'runs-on:' in at least one job"
    exit 1
fi

echo "✅ Basic validation passed!"
