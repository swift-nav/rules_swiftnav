"""Aspect to validate allowed C/C++ dependencies at build time.

This aspect enforces the dependency hierarchy based on tags:
- internal (level 0): Can depend on anything
- prod (level 1): Can depend on prod or safe only
- safe (level 2): Can depend on safe only

Additionally:
- portable targets can only depend on other portable targets
- Targets without level tags (including external dependencies) are ignored
"""

# Provider to carry dependency level information through the dependency graph
DependencyLevelInfo = provider(
    "Information about a target's dependency level",
    fields = {
        "level": "Dependency level (0=internal, 1=prod, 2=safe, None=no level)",
        "portable": "Whether the target is portable",
        "label": "The target's label",
    },
)

def _get_coding_level_from_tags(tags):
    """Extract coding standard level from tags.

    Returns:
        0 for internal, 1 for prod, 2 for safe, None if no level found
    """
    if "internal" in tags:
        return 0
    if "prod" in tags:
        return 1
    if "safe" in tags:
        return 2
    return None

def _level_to_str(level):
    """Convert numeric level to string."""
    if level == 0:
        return "internal"
    if level == 1:
        return "prod"
    if level == 2:
        return "safe"
    return "unknown"

def _is_portable(tags):
    """Check if target is marked as portable."""
    return "portable" in tags

def _check_allowed_cc_deps_impl(target, ctx):
    """Aspect implementation to check allowed C/C++ dependencies."""

    # Skip non-C/C++ targets
    if not CcInfo in target:
        return []

    # Skip if this is not a rule (e.g., a source file)
    if not hasattr(ctx.rule, "attr"):
        return []

    # Get the current target's tags
    current_tags = getattr(ctx.rule.attr, "tags", [])
    current_level = _get_coding_level_from_tags(current_tags)
    current_portable = _is_portable(current_tags)
    label_str = str(target.label)

    # If target has no dependency level, skip validation
    # This includes external dependencies, test libraries, and other untagged targets
    if current_level == None:
        # Check if it's a test target - tests are implicitly internal (level 0)
        if "test" in current_tags or "test_library" in current_tags:
            current_level = 0
        else:
            # Return provider indicating no level (external deps, untagged targets, etc.)
            return [DependencyLevelInfo(
                level = None,
                portable = current_portable,
                label = label_str,
            )]

    # Check dependencies
    deps = getattr(ctx.rule.attr, "deps", [])

    for dep in deps:
        # Get dependency level info from dependency via provider
        if not DependencyLevelInfo in dep:
            # Dependency doesn't have dependency level info - skip it
            continue

        dep_info = dep[DependencyLevelInfo]
        dep_level = dep_info.level
        dep_portable = dep_info.portable

        # If dependency has no level, skip validation
        # This handles external dependencies and untagged targets
        if dep_level == None:
            continue

        # Check dependency level hierarchy
        if dep_level < current_level:
            error_msg = ("ERROR: Target {} (level={}) cannot depend on {} (level={}). " +
                         "Higher level targets can only depend on same or higher level targets.").format(
                target.label,
                _level_to_str(current_level),
                dep_info.label,
                _level_to_str(dep_level),
            )
            fail(error_msg)

        # Check portability requirements
        if current_portable and not dep_portable:
            error_msg = ("ERROR: Target {} is marked as portable but depends on {} which is not portable. " +
                         "Portable targets can only depend on other portable targets.").format(
                target.label,
                dep_info.label,
            )
            fail(error_msg)

    # Return provider for this target
    return [DependencyLevelInfo(
        level = current_level,
        portable = current_portable,
        label = label_str,
    )]

check_allowed_cc_deps = aspect(
    implementation = _check_allowed_cc_deps_impl,
    attr_aspects = ["deps"],
    attrs = {},
)

def _validate_allowed_deps_rule_impl(ctx):
    """Rule that applies the validation aspect to specified targets."""

    # This rule doesn't produce any output, it just triggers the aspect
    output = ctx.actions.declare_file(ctx.label.name + ".validation")
    ctx.actions.write(
        output = output,
        content = "Allowed C/C++ dependency validation passed\n",
    )
    return [DefaultInfo(files = depset([output]))]

validate_allowed_cc_deps = rule(
    implementation = _validate_allowed_deps_rule_impl,
    attrs = {
        "targets": attr.label_list(
            aspects = [check_allowed_cc_deps],
            doc = "Targets to validate",
        ),
    },
    doc = "Validates allowed C/C++ dependencies for specified targets",
)

def validate_all_allowed_cc_deps(name, targets = ["//..."]):
    """Macro to create a validation target for allowed C/C++ dependencies.

    Args:
        name: Name of the validation target
        targets: List of target patterns to validate (default: all targets)
    """
    validate_allowed_cc_deps(
        name = name,
        targets = targets,
        tags = ["manual"],  # Don't build by default, only when explicitly requested
    )
