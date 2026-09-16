#!/usr/bin/env bash

# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

# Overwrites the checked-in checkout script with the generated one.
# Usage: update.sh <generated> <checked-in>

set -o errexit

# bazel run executes from the runfiles tree, so $1 is a rootpath.
cp -f "$1" "$BUILD_WORKSPACE_DIRECTORY/$2"
