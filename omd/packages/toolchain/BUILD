load("@rules_cc//cc:defs.bzl", "cc_toolchain")
load(":cc_toolchain_config.bzl", "cc_toolchain_config")

filegroup(name = "empty")

local_tool_paths = {
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

local_cxx_builtin_include_directories = [
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

cc_toolchain_config(
    name = "local_config",
    compiler = "gcc-13",
    cxx_builtin_include_directories = local_cxx_builtin_include_directories,
    tool_paths = local_tool_paths,
    toolchain_identifier = "local",
)

cc_toolchain(
    name = "local_toolchain",
    all_files = ":empty",
    compiler_files = ":empty",
    dwp_files = ":empty",
    linker_files = ":empty",
    objcopy_files = ":empty",
    static_runtime_lib = ":empty",
    strip_files = ":empty",
    supports_param_files = 0,
    toolchain_config = ":local_config",
    toolchain_identifier = "local",
)

toolchain(
    name = "local",
    exec_compatible_with = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    target_compatible_with = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    toolchain = ":local_toolchain",
    toolchain_type = "@bazel_tools//tools/cpp:toolchain_type",
)

cc_toolchain_config(
    name = "ci_config",
    compiler = "gcc-13",
    cxx_builtin_include_directories = ci_cxx_builtin_include_directories,
    tool_paths = ci_tool_paths,
    toolchain_identifier = "ci",
)

cc_toolchain(
    name = "ci_toolchain",
    all_files = ":empty",
    compiler_files = ":empty",
    dwp_files = ":empty",
    linker_files = ":empty",
    objcopy_files = ":empty",
    static_runtime_lib = ":empty",
    strip_files = ":empty",
    supports_param_files = 0,
    toolchain_config = ":ci_config",
    toolchain_identifier = "ci",
)

toolchain(
    name = "ci",
    exec_compatible_with = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    target_compatible_with = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    toolchain = ":ci_toolchain",
    toolchain_type = "@bazel_tools//tools/cpp:toolchain_type",
)
