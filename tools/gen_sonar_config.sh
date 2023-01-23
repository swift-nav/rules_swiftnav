#!/bin/bash -e

cd $BUILD_WORKSPACE_DIRECTORY

filename="sonar-project.properties"
echo -n "" > $filename

first=1

echo "sonar.sourceEncoding=UTF-8" >> $filename
echo "sonar.sources=\\" >> $filename
for target in $(bazel query //... --noshow_progress); do
    for file in $(bazel run \
        --noshow_progress \
        --ui_event_filters=-info,-stdout,-stderr \
        --@rules_swiftnav//tools:cov_target=$target \
        @rules_swiftnav//tools:cov_files); do
        if [[ $first -eq 1 ]]
        then
            first=0
        else
            echo ",\\" >> $filename
        fi
        echo -n "  $BUILD_WORKSPACE_DIRECTORY/$file" >> $filename
    done
done

echo "" >> $filename
