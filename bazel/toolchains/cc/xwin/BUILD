# Cross compilation to x86_64-pc-windows-msvc from Linux:
# clang-cl, lld-link and llvm-lib from the hermetic LLVM download drive the
# MSVC CRT + Windows SDK provided by @xwin_sysroot.
#
# Note: this toolchain currently serves the Rust builds, it is not yet a general-purpose C++
# toolchain.
load("@rules_cc//cc/toolchains:artifacts.bzl", "cc_artifact_name_pattern")
load("@rules_cc//cc/toolchains:toolchain.bzl", "cc_toolchain")

cc_toolchain(
    name = "windows_msvc_x64",
    args = [
        "//bazel/toolchains/cc/xwin/args:compile_defaults",
        "//bazel/toolchains/cc/xwin/args:sysroot_includes",
        "//bazel/toolchains/cc/xwin/args:link_defaults",
    ],
    artifact_name_patterns = [
        ":executable",
        ":object_file",
        ":static_library",
    ],
    compiler = "clang-cl",
    tags = ["manual"],
    target_system_name = "x86_64-pc-windows-msvc",
    tool_map = "//bazel/toolchains/cc/xwin/tools",
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
    name = "windows_msvc_x64_toolchain",
    exec_compatible_with = [
        "@platforms//os:linux",
        "@platforms//cpu:x86_64",
    ],
    target_compatible_with = [
        "//bazel/platforms:msvc",
        "@platforms//os:windows",
        "@platforms//cpu:x86_64",
    ],
    toolchain = ":windows_msvc_x64",
    toolchain_type = "@bazel_tools//tools/cpp:toolchain_type",
)
