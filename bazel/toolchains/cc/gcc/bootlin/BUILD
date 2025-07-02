load(
    "@rules_cc//cc:cc_toolchain_config.bzl",
    "unix_cc_toolchain_config",
)
load("@rules_cc//cc:defs.bzl", "cc_toolchain")

filegroup(name = "empty")

filegroup(
    name = "bootlin_wrappers",
    srcs = glob(["tool_wrappers/x86_64-linux-*"]),
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
        tool: "tool_wrappers/x86_64-linux-{0}".format(tool)
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
