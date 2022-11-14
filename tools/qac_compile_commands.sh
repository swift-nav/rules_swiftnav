#! /bin/bash
# This script turns the -isystem flag into the -I flag.
# This is needed for Helix QAC to work properly.
# Usage: qac_compile_commands <REFRESH_COMPILE_COMMANDS>

REFRESH_COMPILE_COMMANDS=$1

$REFRESH_COMPILE_COMMANDS
sed -i 's/-isystem/-I/' $BUILD_WORKSPACE_DIRECTORY/compile_commands.json
