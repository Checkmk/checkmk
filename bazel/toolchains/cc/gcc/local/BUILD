load("@bazel_skylib//rules:common_settings.bzl", "string_flag")
load(
    "@rules_cc//cc:cc_toolchain_config.bzl",
    "unix_cc_toolchain_config",
)
load("@rules_cc//cc:defs.bzl", "cc_toolchain")

filegroup(name = "empty")

string_flag(
    name = "gcc_path",
    build_setting_default = "usr_bin",
    visibility = ["//visibility:public"],
)

config_setting(
    name = "opt",
    flag_values = {":gcc_path": "opt"},
)

unix_cc_toolchain_config(
    name = "linux_x86_64_config",
    abi_libc_version = "local",
    abi_version = "local",
    compile_flags = [
        "-fstack-protector",
        "-Wall",
        "-Wunused-but-set-parameter",
        "-Wno-free-nonheap-object",
        "-fno-omit-frame-pointer",
    ],
    compiler = "gcc",
    cpu = "k8",
    cxx_builtin_include_directories = [
        # local
        "/usr/lib/gcc/x86_64-linux-gnu/13/include",
        "/usr/lib/gcc/x86_64-linux-gnu/13/include-fixed",
        # ci
        "/opt/gcc-13.2.0/lib/gcc/x86_64-pc-linux-gnu/13.2.0/include",
        "/opt/gcc-13.2.0/lib/gcc/x86_64-pc-linux-gnu/13.2.0/include-fixed",
        "/opt/gcc-13.2.0/include",
        # generic
        "/include",
        "/usr/include",
        "/usr/lib64/",
    ],
    cxx_flags = ["-std=c++20"],
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
    tool_paths = select(
        {
            "//conditions:default": {
                "ar": "/usr/bin/gcc-ar-13",
                "cpp": "/usr/bin/cpp-13",
                "gcc": "/usr/bin/gcc-13",
                "ld": "/usr/bin/ld",
                "nm": "/usr/bin/gcc-nm-13",
                "objdump": "/usr/bin/objdump",
                "strip": "/usr/bin/strip",
                "objcopy": "/usr/bin/objcopy",
            },
            ":opt": {
                "ar": "/opt/gcc-13.2.0/bin/gcc-ar-13",
                "cpp": "/opt/gcc-13.2.0/bin/cpp-13",
                "gcc": "/opt/gcc-13.2.0/bin/gcc-13",
                "ld": "/opt/gcc-13.2.0/bin/ld",
                "nm": "/opt/gcc-13.2.0/bin/gcc-nm-13",
                "objdump": "/opt/gcc-13.2.0/bin/objdump",
                "strip": "/opt/gcc-13.2.0/bin/strip",
                "objcopy": "/opt/gcc-13.2.0/bin/objcopy",
            },
        },
    ),
    toolchain_identifier = "linux_x86_64",
    unfiltered_compile_flags = [
        "-Wno-builtin-macro-redefined",
        "-D__DATE__=\"redacted\"",
        "-D__TIMESTAMP__=\"redacted\"",
        "-D__TIME__=\"redacted\"",
        "-fno-canonical-system-headers",
    ],
)

cc_toolchain(
    name = "linux_x86_64_toolchain",
    all_files = ":empty",
    compiler_files = ":empty",
    dwp_files = ":empty",
    linker_files = ":empty",
    objcopy_files = ":empty",
    static_runtime_lib = ":empty",
    strip_files = ":empty",
    supports_param_files = 0,
    toolchain_config = ":linux_x86_64_config",
    toolchain_identifier = "linux_x86_64",
)

toolchain(
    name = "linux_x86_64",
    exec_compatible_with = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    target_compatible_with = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    toolchain = ":linux_x86_64_toolchain",
    toolchain_type = "@bazel_tools//tools/cpp:toolchain_type",
)
