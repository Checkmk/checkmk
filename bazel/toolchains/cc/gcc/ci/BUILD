load(
    "@rules_cc//cc:cc_toolchain_config.bzl",
    "unix_cc_toolchain_config",
)
load("@rules_cc//cc:defs.bzl", "cc_toolchain")

filegroup(name = "empty")

unix_cc_toolchain_config(
    name = "ci_config",
    abi_libc_version = "local",
    abi_version = "local",
    compile_flags = [
        "-fstack-protector",
        "-Wall",
        "-Wunused-but-set-parameter",
        "-Wno-free-nonheap-object",
        "-fno-omit-frame-pointer",
    ],
    compiler = "gcc-13",
    cpu = "k8",
    cxx_builtin_include_directories = [
        "/opt/gcc-13.2.0/lib/gcc/x86_64-pc-linux-gnu/13.2.0/include",
        "/opt/gcc-13.2.0/lib/gcc/x86_64-pc-linux-gnu/13.2.0/include-fixed",
        "/opt/gcc-13.2.0/include",
        "/usr/include",
        "/usr/lib64/",
    ],
    cxx_flags = ["-std=c++20"],
    dbg_compile_flags = ["-g"],
    host_system_name = "local",
    link_flags = [
        # DO NOT USE -fuse-ld=gold here: it is not available on sles15sp5
        # However, I still don't understand why it would fail as were hardcoding the ld path for the CI toolchain
        "-Wl,-no-as-needed",
        "-Wl,-z,relro,-z,now",
        "-B/opt/bin",
    ],
    link_libs = [
        "-lstdc++",
        "-lm",
    ],
    opt_compile_flags = [
        "-g0",
        "-O2",
        "-D_FORTIFY_SOURCE=1",
        "-DNDEBUG",
        "-ffunction-sections",
        "-fdata-sections",
    ],
    opt_link_flags = ["-Wl,--gc-sections"],
    target_libc = "local",
    target_system_name = "local",
    tool_paths = {
        "ar": "/opt/gcc-13.2.0/bin/gcc-ar-13",
        "cpp": "/opt/gcc-13.2.0/bin/cpp-13",
        "gcc": "/opt/gcc-13.2.0/bin/gcc-13",
        "ld": "/opt/gcc-13.2.0/bin/ld",
        "nm": "/opt/gcc-13.2.0/bin/gcc-nm-13",
        "objdump": "/opt/gcc-13.2.0/bin/objdump",
        "strip": "/opt/gcc-13.2.0/bin/strip",
        "objcopy": "/opt/gcc-13.2.0/bin/objcopy",
    },
    toolchain_identifier = "ci",
    unfiltered_compile_flags = [
        "-Wno-builtin-macro-redefined",
        "-D__DATE__=\"redacted\"",
        "-D__TIMESTAMP__=\"redacted\"",
        "-D__TIME__=\"redacted\"",
        "-fno-canonical-system-headers",
    ],
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
