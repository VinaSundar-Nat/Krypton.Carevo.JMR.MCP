#!/bin/bash
set -e
set -o pipefail

function cleanAndRebuild(){
    ROOT_DIR=$(pwd)

    cd $1
    echo "Cleaning and rebuilding in directory: $1"
    uv cache clean
    uv sync --reinstall
    uv add -r ./requirements.txt
    uv build

    cd "$ROOT_DIR"
}

# Clean and rebuild jmr-lib
cleanAndRebuild  "./libraries/jmr-lib"
# Clean and rebuild jmr-svc
cleanAndRebuild "./servers/jmr-svc"