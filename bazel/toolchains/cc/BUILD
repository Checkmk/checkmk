load(
    "@forked_cc_toolchain_config//:unix_cc_toolchain_config.bzl",
    unix_cc_toolchain_config = "cc_toolchain_config",
)
load("@rules_cc//cc:defs.bzl", "cc_toolchain")

filegroup(name = "empty")

COMPILE_FLAGS = [
    "-fstack-protector",
    "-Wall",
    "-Wunused-but-set-parameter",
    "-Wno-free-nonheap-object",
    "-fno-omit-frame-pointer",
]

CXX_FLAGS = ["-std=c++20"]

DBG_COMPILE_FLAGS = ["-g"]

LINK_FLAGS = [
    # DO NOT USE -fuse-ld=gold here: it is not available on sles15sp5
    # However, I still don't understand why it would fail as were hardcoding the ld path for the CI toolchain
    "-Wl,-no-as-needed",
    "-Wl,-z,relro,-z,now",
    "-pass-exit-codes",
]

linux_gcc13_link_flags = ["-B/usr/bin"]

ci_link_flags = ["-B/opt/bin"]

LINK_LIBS = ["-lm"]

OPT_COMPILE_FLAGS = [
    "-g0",
    "-O2",
    "-D_FORTIFY_SOURCE=1",
    "-DNDEBUG",
    "-ffunction-sections",
    "-fdata-sections",
]

OPT_LINK_FLAGS = ["-Wl,--gc-sections"]

UNFILTERED_COMPILE_FLAGS = [
    "-fno-canonical-system-headers",
    "-Wno-builtin-macro-redefined",
    "-D__DATE__=\"redacted\"",
    "-D__TIMESTAMP__=\"redacted\"",
    "-D__TIME__=\"redacted\"",
]

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
    "linux_gcc13": (
        linux_gcc13_cxx_builtin_include_directories,
        linux_gcc13_tool_paths,
        linux_gcc13_link_flags,
    ),
    "ci": (
        ci_cxx_builtin_include_directories,
        ci_tool_paths,
        ci_link_flags,
    ),
}

[
    unix_cc_toolchain_config(
        name = identifier + "_config",
        abi_libc_version = "local",
        abi_version = "local",
        compile_flags = COMPILE_FLAGS,
        compiler = "gcc-13",
        cpu = "k8",
        cxx_builtin_include_directories = cxx_builtin_include_directories,
        cxx_flags = CXX_FLAGS,
        dbg_compile_flags = DBG_COMPILE_FLAGS,
        host_system_name = "local",
        link_flags = LINK_FLAGS + link_flags,
        link_libs = LINK_LIBS,
        opt_compile_flags = OPT_COMPILE_FLAGS,
        opt_link_flags = OPT_LINK_FLAGS,
        target_libc = "local",
        target_system_name = "local",
        tool_paths = tool_paths,
        toolchain_identifier = identifier,
        unfiltered_compile_flags = UNFILTERED_COMPILE_FLAGS,
    )
    for identifier, (
        cxx_builtin_include_directories,
        tool_paths,
        link_flags,
    ) in TOOLCHAINS.items()
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
