#! /bin/bash
# This one-line script turns the -isystem flag into the -I flag. This is needed for Helix QAC to work properly.

sed -i 's/-isystem/-I/' $BUILD_WORKSPACE_DIRECTORY/compile_commands.json
