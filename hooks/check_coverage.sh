#!/bin/bash
# Kudos to chatgpt4 and everybody who (involuntarily) provided training material for this script.
set -e


# Define path to a file that perists the current test coverage percentage as
# the first argument to the script, commonly via args in .pre-commit-config.yaml
COVERAGE_FILE=$1

# Run tests and get coverage
COVERAGE=$(pytest --cov | grep 'TOTAL' | awk '{print $NF}' | sed 's/%//')

# Check if coverage file exists and get previous coverage
if [ -f $COVERAGE_FILE ]; then
    PREVIOUS_COVERAGE=$(cat $COVERAGE_FILE)
else
    echo "0" > $COVERAGE_FILE
    PREVIOUS_COVERAGE=0
fi

# Check if coverage dropped using bc for floating point comparison
if (( $(echo "$COVERAGE < $PREVIOUS_COVERAGE" | bc -l) )); then
    echo "This commit drops test coverage from $PREVIOUS_COVERAGE% to $COVERAGE%. Test coverage must not decrease!"
    exit 1
fi

# Save new coverage
echo $COVERAGE > $COVERAGE_FILE
