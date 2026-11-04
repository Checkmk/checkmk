"""C++ runtime libraries that Checkmk ships."""

# Below x86_64-checkmk-linux-gnu/sysroot/lib.
CPP_LIBS_ELF = [
    "libgcc_s.so.1",
    "libstdc++.so.6.0.33",
]

# (link name, target): the toolchain only ships the versioned libstdc++.
SYMLINK_MAPPINGS = [
    ("libstdc++.so", "libstdc++.so.6.0.33"),
    ("libstdc++.so.6", "libstdc++.so.6.0.33"),
]
