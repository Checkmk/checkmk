# Cross compilation to x86_64-pc-windows-msvc from Linux: clang-cl, lld-link and
# llvm-lib from the hermetic LLVM download drive the MSVC CRT + Windows SDK
# provided by @xwin_sysroot. It serves both rustc's linker and cargo's build
# scripts (via CC/AR/CFLAGS) and Bazel's own cc_* actions.
#
# Only the cc_* actions follow -c; see args/mode. The Rust-side command lines
# stay on the release settings, see args/build_script.
#
# README.md has the design: the vcxproj mapping, the CRT and .pdb reasoning, and
# the rules_rust behaviours this all works around.

load("@rules_cc//cc/toolchains:args.bzl", "cc_args")
load("@rules_cc//cc/toolchains:artifacts.bzl", "cc_artifact_name_pattern")
load("@rules_cc//cc/toolchains:feature.bzl", "cc_feature")
load("@rules_cc//cc/toolchains:toolchain.bzl", "cc_toolchain")

cc_toolchain(
    name = "x86_64_windows_msvc",
    args = [
        "//bazel/toolchains/cc/clang/xwin/args:target_triple",
        "//bazel/toolchains/cc/clang/xwin/args:cpp_exceptions",
        "//bazel/toolchains/cc/clang/args:no_absolute_paths_for_builtins",
        "//bazel/toolchains/cc/clang/xwin/args:windows_sysroot",
        "//bazel/toolchains/cc/clang/xwin/args:machine_x64",
        "//bazel/toolchains/cc/clang/xwin/args:sysroot_libs",
        # Dead for real actions (requires_none): these expand only for the
        # Rust-side command lines, see the header.
        "//bazel/toolchains/cc/clang/xwin/args/build_script:release_defaults",
    ],
    artifact_name_patterns = [
        ":executable",
        ":object_file",
        ":static_library",
    ],
    compiler = "clang-cl",
    enabled_features = [
        ":replace_legacy_action_configs",
        ":parse_showincludes",
        "//bazel/toolchains/cc/clang/args/msvc:features",
    ],
    known_features = [
        ":replace_legacy_action_configs",
        ":parse_showincludes",
        "//bazel/toolchains/cc/clang/args/msvc:features",
        "//bazel/toolchains/cc/clang/xwin/args/mode:features",
    ],
    tags = ["manual"],
    target_system_name = "x86_64-pc-windows-msvc",
    tool_map = "//bazel/toolchains/cc/clang/xwin/tools",
)

cc_feature(
    name = "replace_legacy_action_configs",
    args = [],
    feature_name = "experimental_replace_legacy_action_config_features",
)

cc_feature(
    name = "parse_showincludes",
    args = [":showincludes_args"],
    feature_name = "parse_showincludes",
)

cc_args(
    name = "showincludes_args",
    actions = ["@rules_cc//cc/toolchains/actions:source_compile_actions"],
    args = ["/showIncludes"],
    requires_not_none = "@rules_cc//cc/toolchains/variables:source_file",
)

cc_artifact_name_pattern(
    name = "executable",
    category = "@rules_cc//cc/toolchains/artifacts:executable",
    extension = ".exe",
    prefix = "",
)

cc_artifact_name_pattern(
    name = "object_file",
    category = "@rules_cc//cc/toolchains/artifacts:object_file",
    extension = ".obj",
    prefix = "",
)

cc_artifact_name_pattern(
    name = "static_library",
    category = "@rules_cc//cc/toolchains/artifacts:static_library",
    extension = ".lib",
    prefix = "",
)

toolchain(
    name = "x86_64_windows_msvc_toolchain",
    exec_compatible_with = [
        "@platforms//os:linux",
        "@platforms//cpu:x86_64",
    ],
    target_compatible_with = [
        "//bazel/platforms:msvc",
        "@platforms//os:windows",
        "@platforms//cpu:x86_64",
    ],
    toolchain = ":x86_64_windows_msvc",
    toolchain_type = "@bazel_tools//tools/cpp:toolchain_type",
    visibility = ["//visibility:public"],
)
