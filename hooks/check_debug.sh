#!/bin/bash
# Kudos to chatgpt4 and everybody who (involuntarily) provided training material for this script.
set -e

# Initialize empty arrays for files and directories to exclude
EXCLUDE_FILES=()
EXCLUDE_DIRS=()

# Parse the arguments
while (( "$#" )); do
  case "$1" in
    --exclude-files=*)
      IFS=',' read -ra EXCLUDE_FILES <<< "${1#*=}"
      shift
      ;;
    --exclude-dirs=*)
      IFS=',' read -ra EXCLUDE_DIRS <<< "${1#*=}"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Build the exclude options for grep
EXCLUDES=""
for FILE in "${EXCLUDE_FILES[@]}"; do
    EXCLUDES="$EXCLUDES --exclude=$FILE"
done

for DIR in "${EXCLUDE_DIRS[@]}"; do
    EXCLUDES="$EXCLUDES --exclude-dir=$DIR"
done

# Check for the word "DEBUG" in the files
if grep -Rw $EXCLUDES "DEBUG" .; then
    echo "Found the word 'DEBUG' in the files above. Please remove it before committing."
    exit 1
fi
