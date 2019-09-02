#!/bin/bash
# Remove source files of enterprise / managed specific components from the
# given source archives before publishing them

set -e -o pipefail

SRC_PATHS=$@
if [ -z "$SRC_PATHS" ]; then 
    echo "$0 PACKAGE..." 
    echo "Example: $0 /path/to/package.tar.gz"
    exit 1
fi

for SRC_PATH in $SRC_PATHS; do
    FILENAME="${SRC_PATH##*/}"
    DIRNAME="${FILENAME%.tar.gz}"
    REMOVE_DIRS=""
    echo "=> $SRC_PATH"
     
    if tar tvzf $SRC_PATH | grep "$DIRNAME/managed" >/dev/null; then 
        echo "Found CME specific components..."
        REMOVE_DIRS+=" $DIRNAME/managed"
    fi
     
    if tar tvzf $SRC_PATH | grep "$DIRNAME/enterprise" >/dev/null; then 
        echo "Found CEE specific components..."
        REMOVE_DIRS+=" $DIRNAME/enterprise"
    fi
    
    if [ -z "$REMOVE_DIRS" ]; then
        echo "Found no files to be removed. Done."
        continue
    fi
    
    echo "Removing$REMOVE_DIRS..."
    gunzip -c "$SRC_PATH" | tar -v --delete$REMOVE_DIRS | gzip > "$SRC_PATH.new"
    mv "$SRC_PATH.new" "$SRC_PATH"
    
    echo "Checking for remaining CEE/CME files..."
    if tar tvzf $SRC_PATH | grep -E "$DIRNAME/(managed|enterprise)"; then
        echo "ERROR: Still found some CEE/CME specific components."
        exit 1
    fi
    echo "Done."
done
