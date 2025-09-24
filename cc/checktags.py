#!/bin/env python

import subprocess
import json
import os
import re

os.chdir(os.environ["BUILD_WORKSPACE_DIRECTORY"])

targets = {}

def run_bazel(args):
    #print(args)
    proc = subprocess.run(["bazel"] + args, capture_output=True, text=True)
    return str(proc.stdout)


def get_target_list(kind):
    stdout = run_bazel(["cquery", f"kind(\"{kind}\", //...)", "--output=label"])
    lines =  stdout.split('\n')
    ret = [l.split(' ')[0] for l in lines]
    return ret


def maybe_add_target(json):
    global targets
    if 'target' not in json:
        return
    if 'rule' not in json['target']:
        return
    t = json['target']['rule']

    if t['ruleClass'] not in ["cc_library", "cc_binary", "cc_test", "cmake"]:
        return

    name = t['name']


    if name in targets:
        return

    #print(name)

    targets[name] = {}
    targets[name]['tags'] = []
    targets[name]['deps'] = []

    for a in t['attribute']:
        if a['name'] == 'tags':
            if 'stringListValue' in a:
                targets[name]['tags'] = a['stringListValue']

        if a['name'] == 'deps':
            if 'stringListValue' in a:
                targets[name]['deps'] = a['stringListValue']


def process_deps_for_target(name):
    global targets
    if name == '':
        return
    if name in targets:
        return

    stdout = run_bazel(["cquery", f"\"{name}\"", "--output=jsonproto"])
    info = json.loads(stdout)
    maybe_add_target(info['results'][0])

    stdout = run_bazel(["cquery", f"kind(\"cc_library\", deps(\"{name}\"))", "--output=jsonproto"])
    info = json.loads(stdout)

    for lib in info['results']:
        maybe_add_target(lib)

#for t in get_target_list("cc_binary"):
    #process_deps_for_target(t)
#for t in get_target_list("cc_test"):
    #process_deps_for_target(t)
#for t in get_target_list("cc_library"):
    #process_deps_for_target(t)

def process_target_list(json):
    if 'results' not in json:
        return
    for t in json['results']:
        maybe_add_target(t)

def add_all_from_query(key):
    stdout = run_bazel(["cquery", key, "--output=jsonproto"])
    process_target_list(json.loads(stdout))

print("Loading targets")
add_all_from_query("kind(\"cc_binary\", //...)")
add_all_from_query("kind(\"cc_test\", //...)")
add_all_from_query("kind(\"cc_library\", //...)")
add_all_from_query("deps(kind(\"cc_binary\", //...))")
add_all_from_query("deps(kind(\"cc_test\", //...))")
add_all_from_query("deps(kind(\"cc_library\", //...))")

def get_level_as_num(name):
    if 'internal' in targets[name]['tags']:
        return 0
    if 'prod' in targets[name]['tags']:
        return 1
    if 'safe' in targets[name]['tags']:
        return 2
    return None

def level_to_str(level):
    if level == 0:
        return "internal"
    if level == 1:
        return "prod"
    if level == 2:
        return "safe"
    assert False

# Targets which don't belong to swift and won't follow the same tagging scheme in bazel
whitelist = [
    r"@eigen//.*",
    r"@g(oogle)*test//.*",
    r"@rules_fuzzing//.*",
    r"@benchmark//.*",
    r"@benchmark//.*",
    r"@rapidcheck//.*",
    r"@gmock-global//.*",
    r"@check//.*",
    r"@nanopb//.*",
    r"@@.*",
    r"@bazel.*",
    r"@gflags//.*",
    r"@json//.*",
    r"@fast_csv//.*",
    r"@yaml-cpp//.*",
    r"@nlopt//.*",
    # libfuzzer targets
    r".*_raw_",
]

def is_whitelisted(name):
    for r in whitelist:
        if re.match(r, name):
            return True

    return False

def validate_target(name):
    if is_whitelisted(name):
        return

    level = get_level_as_num(name)
    portable = False
    if 'portable' in targets[name]['tags']:
        portable = True

    if level is None:
        print(f"ERROR: Target {name} doesn't have a coding standard level")
    else:
        for d in targets[name]['deps']:
            if d not in targets:
                print(f"{d} not found in bazel....")
                assert d in targets
            if not is_whitelisted(d):
                dep_level = get_level_as_num(d)
                if dep_level is None:
                    print(f"ERROR: Target {name} has a coding standard level but depends on {d} which doesn't")
                else:
                    if dep_level < level:
                        print(f"ERROR: Target {name} depends on {d} which has a lower coding standard level ({level_to_str(level)} vs {level_to_str(dep_level)}")

                    if portable:
                        if 'portable' not in targets[d]['tags']:
                            print(f"ERROR: Target {name} is a portable target but depends on {d} which is not portable")

for t in sorted(targets.keys()):
    validate_target(t)






