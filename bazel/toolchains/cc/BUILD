load(
    "@rules_cc//cc:cc_toolchain_config.bzl",
    "unix_cc_toolchain_config",
)
load("@rules_cc//cc:defs.bzl", "cc_toolchain")

filegroup(name = "empty")

unix_cc_toolchain_config(
    name = "linux_gcc13_config",
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
        "/usr/lib/gcc/x86_64-linux-gnu/13/include",
        "/usr/lib/gcc/x86_64-linux-gnu/13/include-fixed",
        "/include",
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
        "-B/usr/bin",
        "-pass-exit-codes",
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
        "ar": "/usr/bin/gcc-ar-13",
        "cpp": "/usr/bin/cpp-13",
        "gcc": "/usr/bin/gcc-13",
        "ld": "/usr/bin/ld",
        "nm": "/usr/bin/gcc-nm-13",
        "objdump": "/usr/bin/objdump",
        "strip": "/usr/bin/strip",
        "objcopy": "/usr/bin/objcopy",
    },
    toolchain_identifier = "linux_gcc13",
    unfiltered_compile_flags = [
        "-Wno-builtin-macro-redefined",
        "-D__DATE__=\"redacted\"",
        "-D__TIMESTAMP__=\"redacted\"",
        "-D__TIME__=\"redacted\"",
        "-fno-canonical-system-headers",
    ],
)

cc_toolchain(
    name = "linux_gcc13_toolchain",
    all_files = ":empty",
    compiler_files = ":empty",
    dwp_files = ":empty",
    linker_files = ":empty",
    objcopy_files = ":empty",
    static_runtime_lib = ":empty",
    strip_files = ":empty",
    supports_param_files = 0,
    toolchain_config = ":linux_gcc13_config",
    toolchain_identifier = "linux_gcc13",
)

toolchain(
    name = "linux_gcc13",
    exec_compatible_with = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    target_compatible_with = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    toolchain = ":linux_gcc13_toolchain",
    toolchain_type = "@bazel_tools//tools/cpp:toolchain_type",
)

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

unix_cc_toolchain_config(
    name = "clang19_config",
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
        # List obtained from `clang-19 -E -xc++ - -v < /dev/null` and `realpath`.
        "/usr/include/c++/13",
        "/usr/include/x86_64-linux-gnu/c++/13",
        "/usr/include/c++/13/backward",
        "/usr/lib/llvm-19/lib/clang/19/include",
        "/usr/include/x86_64-linux-gnu",
        "/usr/include",
    ],
    cxx_flags = ["-std=c++20"],
    dbg_compile_flags = ["-g"],
    host_system_name = "local",
    link_flags = [
        # DO NOT USE -fuse-ld=gold here: it is not available on sles15sp5
        # However, I still don't understand why it would fail as were hardcoding the ld path for the CI toolchain
        "-Wl,-no-as-needed",
        "-Wl,-z,relro,-z,now",
        "-B/usr/bin",
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
        "ar": "/usr/bin/llvm-ar-19",
        "cpp": "/usr/bin/clang-cpp-19",
        "gcc": "/usr/bin/clang-19",
        "ld": "/usr/bin/ld",
        "nm": "/usr/bin/llvm-nm-19",
        "objdump": "/usr/bin/llvm-objdump-19",
        "strip": "/usr/bin/llvm-strip-19",
        "objcopy": "/usr/bin/llvm-objcopy-19",
    },
    toolchain_identifier = "clang19",
    unfiltered_compile_flags = [
        "-Wno-builtin-macro-redefined",
        "-D__DATE__=\"redacted\"",
        "-D__TIMESTAMP__=\"redacted\"",
        "-D__TIME__=\"redacted\"",
    ],
)

cc_toolchain(
    name = "clang19_toolchain",
    all_files = ":empty",
    compiler_files = ":empty",
    dwp_files = ":empty",
    linker_files = ":empty",
    objcopy_files = ":empty",
    static_runtime_lib = ":empty",
    strip_files = ":empty",
    supports_param_files = 0,
    toolchain_config = ":clang19_config",
    toolchain_identifier = "clang19",
)

toolchain(
    name = "clang19",
    exec_compatible_with = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    target_compatible_with = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    toolchain = ":clang19_toolchain",
    toolchain_type = "@bazel_tools//tools/cpp:toolchain_type",
)

filegroup(
    name = "bootlin_wrappers",
    srcs = glob(["private/bootlin/tool_wrappers/x86_64-linux-*"]),
)

filegroup(
    name = "bootlin_files",
    srcs = [
        ":bootlin_wrappers",
        "@gcc-linux-x86_64//:all_files",
    ],
)

unix_cc_toolchain_config(
    name = "bootlin_toolchain_config",
    abi_libc_version = "local",
    abi_version = "local",
    compile_flags = [
        "-no-canonical-prefixes",
        "-fno-canonical-system-headers",
        "--sysroot=external/_main~_repo_rules~gcc-linux-x86_64/x86_64-buildroot-linux-gnu/sysroot",
        "-fstack-protector",
        "-Wall",
        "-Wunused-but-set-parameter",
        "-Wno-free-nonheap-object",
        "-fno-omit-frame-pointer",
    ],
    compiler = "gcc",
    cpu = "k8",
    cxx_flags = ["-std=c++17"],
    dbg_compile_flags = ["-g"],
    host_system_name = "local",
    link_flags = [
        "-Wl,-no-as-needed",
        "-Wl,-z,relro,-z,now",
        "-pass-exit-codes",
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
        tool: "private/bootlin/tool_wrappers/x86_64-linux-{0}".format(tool)
        for tool in [
            "ar",
            "cpp",
            "gcc",
            "gcov",
            "ld",
            "nm",
            "objdump",
            "strip",
        ]
    },
    toolchain_identifier = "bootlin_toolchain_config",
)

cc_toolchain(
    name = "bootlin_cc_toolchain",
    all_files = ":bootlin_files",
    ar_files = ":bootlin_files",
    compiler_files = ":bootlin_files",
    dwp_files = ":empty",
    linker_files = ":bootlin_files",
    objcopy_files = ":empty",
    strip_files = ":empty",
    toolchain_config = ":bootlin_toolchain_config",
)

toolchain(
    name = "bootlin_toolchain",
    exec_compatible_with = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    target_compatible_with = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    toolchain = "bootlin_cc_toolchain",
    toolchain_type = "@bazel_tools//tools/cpp:toolchain_type",
)
