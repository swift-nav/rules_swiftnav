# Copyright (c) 2022 Synopsys, Inc. All rights reserved worldwide.
#
# This file describes the aspect that gen_script.bzl will apply to
# a build target to get all of the actions that that need to run
# to build that target. Aspects are recursively applied, so this
# will run for each target in the tree, starting from the leaf nodes
ActionInfo = provider(fields=["actions"])

DEPENDENCY_TYPES = ["deps", "runtime_deps"]
EXTENDED_DEPENDENCY_RULE_KINDS = ["sh_binary", "sh_library", "filegroup"]
EXTENDED_DEPENDENCY_TYPES = ["srcs", "data"]


def _collect_actions_impl(tgt, ctx):
    # Decide what set of dependency types we're using
    dependency_types = list(DEPENDENCY_TYPES)
    if ctx.rule.kind in EXTENDED_DEPENDENCY_RULE_KINDS:
        dependency_types.extend(EXTENDED_DEPENDENCY_TYPES)

    # Collect the dependencies of the current target of the types specified
    deps = []
    for dep_type in dependency_types:
        deps.extend(getattr(ctx.rule.attr, dep_type, []))

    # Get the list of actions from each of those dependencies where
    # this Aspect has already run
    actions = []
    for dep_actions in [x[ActionInfo].actions for x in deps if ActionInfo in x]:
        actions.append(dep_actions)

    # Return an ActionInfo provider containing all of the actions for this
    # target and all targets it depends on
    return [ActionInfo(actions=depset(direct=tgt.actions, transitive=actions))]


collect_actions = aspect(
    implementation=_collect_actions_impl,
    attr_aspects=DEPENDENCY_TYPES + EXTENDED_DEPENDENCY_TYPES,
)
