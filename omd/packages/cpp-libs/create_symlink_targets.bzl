"""Macro for creating pkg_mklink targets from symlink mappings."""

load("@rules_pkg//pkg:mappings.bzl", "pkg_mklink")

def create_symlink_targets(name_prefix, mappings):
    """Creates pkg_mklink targets from symlink mappings.

    Args:
        name_prefix: Prefix for generated target names (e.g., "usr")
        mappings: List of (link_name, target) tuples

    Returns:
        List of target labels for the created pkg_mklink targets
    """
    targets = []
    for link_name, target in mappings:
        target_name = "{}_symlink_{}".format(
            name_prefix,
            link_name.replace(".", "_").replace("-", "_"),
        )
        pkg_mklink(
            name = target_name,
            link_name = "lib/{}".format(link_name),
            target = target,
            tags = ["manual"],
        )
        targets.append(":{}".format(target_name))
    return targets
