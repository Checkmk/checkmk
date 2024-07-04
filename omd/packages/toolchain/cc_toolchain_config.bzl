load("@bazel_tools//tools/build_defs/cc:action_names.bzl", "ACTION_NAMES")
load(
    "@bazel_tools//tools/cpp:cc_toolchain_config_lib.bzl",
    "feature",
    "flag_group",
    "flag_set",
    "tool_path",
)

all_link_actions = [
    ACTION_NAMES.cpp_link_executable,
    ACTION_NAMES.cpp_link_dynamic_library,
    ACTION_NAMES.cpp_link_nodeps_dynamic_library,
]

prefix = "/opt/gcc-13.2.0"

def _impl(ctx):
    tool_paths = [
        tool_path(
            name = "gcc",
            path = prefix + "/bin/gcc-13",
        ),
        tool_path(
            name = "ld",
            path = prefix + "/bin/ld",
        ),
        tool_path(
            name = "ar",
            path = prefix + "/bin/gcc-ar-13",
        ),
        tool_path(
            name = "cpp",
            path = prefix + "/bin/cpp-13",
        ),
        tool_path(
            name = "gcov",
            path = prefix + "/bin/gcov-13",
        ),
        tool_path(
            name = "nm",
            path = prefix + "/bin/gcc-nm-13",
        ),
        tool_path(
            name = "objdump",
            path = prefix + "/bin/objdump",
        ),
        tool_path(
            name = "strip",
            path = prefix + "/bin/strip",
        ),
    ]

    features = [
        feature(
            name = "default_linker_flags",
            enabled = True,
            flag_sets = [
                flag_set(
                    actions = all_link_actions,
                    flag_groups = ([
                        flag_group(
                            flags = [
                                "-lstdc++",
                            ],
                        ),
                    ]),
                ),
            ],
        ),
    ]

    return cc_common.create_cc_toolchain_config_info(
        ctx = ctx,
        features = features,
        cxx_builtin_include_directories = [
            prefix + "/lib/gcc/x86_64-pc-linux-gnu/13.2.0/include",
            prefix + "/lib/gcc/x86_64-pc-linux-gnu/13.2.0/include-fixed",
            prefix + "/include",
            "/usr/include",
            "/usr/lib64/",
        ],
        toolchain_identifier = "local",
        host_system_name = "local",
        target_system_name = "local",
        target_cpu = "k8",
        target_libc = "unknown",
        compiler = "gcc-13",
        abi_version = "unknown",
        abi_libc_version = "unknown",
        tool_paths = tool_paths,
    )

cc_toolchain_config = rule(
    implementation = _impl,
    attrs = {},
    provides = [CcToolchainConfigInfo],
)
