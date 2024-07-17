load("@rules_cc//cc:defs.bzl", "cc_toolchain")
load(":cc_toolchain_config.bzl", "cc_toolchain_config")

filegroup(name = "empty")

linux_gcc13_tool_paths = {
    "ar": "/usr/bin/gcc-ar-13",
    "cpp": "/usr/bin/cpp-13",
    "gcc": "/usr/bin/gcc-13",
    "gcov": "/usr/bin/gcov-13",
    "ld": "/usr/bin/ld",
    "nm": "/usr/bin/gcc-nm-13",
    "objdump": "/usr/bin/objdump",
    "strip": "/usr/bin/strip",
    "llvm-cov": "/bin/false",  # Optional on master.
    "objcopy": "/usr/bin/objcopy",
}

linux_gcc13_cxx_builtin_include_directories = [
    "/usr/lib/gcc/x86_64-linux-gnu/13/include",
    "/usr/lib/gcc/x86_64-linux-gnu/13/include-fixed",
    "/include",
    "/usr/include",
    "/usr/lib64/",
]

ci_tool_paths = {
    "ar": "/opt/gcc-13.2.0/bin/gcc-ar-13",
    "cpp": "/opt/gcc-13.2.0/bin/cpp-13",
    "gcc": "/opt/gcc-13.2.0/bin/gcc-13",
    "gcov": "/opt/gcc-13.2.0/bin/gcov-13",
    "ld": "/opt/gcc-13.2.0/bin/ld",
    "nm": "/opt/gcc-13.2.0/bin/gcc-nm-13",
    "objdump": "/opt/gcc-13.2.0/bin/objdump",
    "strip": "/opt/gcc-13.2.0/bin/strip",
    "llvm-cov": "/bin/false",  # Optional on master.
    "objcopy": "/opt/gcc-13.2.0/bin/objcopy",
}

ci_cxx_builtin_include_directories = [
    "/opt/gcc-13.2.0/lib/gcc/x86_64-pc-linux-gnu/13.2.0/include",
    "/opt/gcc-13.2.0/lib/gcc/x86_64-pc-linux-gnu/13.2.0/include-fixed",
    "/opt/gcc-13.2.0/include",
    "/usr/include",
    "/usr/lib64/",
]

TOOLCHAINS = {
    "linux_gcc13": (linux_gcc13_cxx_builtin_include_directories, linux_gcc13_tool_paths),
    "ci": (ci_cxx_builtin_include_directories, ci_tool_paths),
}

[
    cc_toolchain_config(
        name = identifier + "_config",
        compiler = "gcc-13",
        cxx_builtin_include_directories = cxx_builtin_include_directories,
        tool_paths = tool_paths,
        toolchain_identifier = identifier,
    )
    for identifier, (cxx_builtin_include_directories, tool_paths) in TOOLCHAINS.items()
]

[cc_toolchain(
    name = identifier + "_toolchain",
    all_files = ":empty",
    compiler_files = ":empty",
    dwp_files = ":empty",
    linker_files = ":empty",
    objcopy_files = ":empty",
    static_runtime_lib = ":empty",
    strip_files = ":empty",
    supports_param_files = 0,
    toolchain_config = ":" + identifier + "_config",
    toolchain_identifier = identifier,
) for identifier in TOOLCHAINS]

[toolchain(
    name = identifier,
    exec_compatible_with = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    target_compatible_with = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    toolchain = ":" + identifier + "_toolchain",
    toolchain_type = "@bazel_tools//tools/cpp:toolchain_type",
) for identifier in TOOLCHAINS]
