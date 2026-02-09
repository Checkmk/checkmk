"""Symlink mappings for Bootlin GCC toolchain C++ runtime libraries.

This file defines the symlink structure for libstdc++.
The mappings are used by packaging rules to create pkg_mklink targets.
"""

# List of (link_name, target) tuples for creating pkg_mklink targets
SYMLINK_MAPPINGS = [
    ("libstdc++.so", "libstdc++.so.6"),
    ("libstdc++.so.6", "libstdc++.so.6.0.33"),
]
