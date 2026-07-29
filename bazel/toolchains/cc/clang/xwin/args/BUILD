# Arguments that come from the @xwin_sysroot side of the toolchain: the target it
# can produce, its include and library paths, and the MSVC dialect choices the
# agents/wnx vcxprojs make.

load("@rules_cc//cc/toolchains:args.bzl", "cc_args")

package(default_visibility = ["//bazel/toolchains/cc/clang:__subpackages__"])

cc_args(
    name = "target_triple",
    actions = [
        "@rules_cc//cc/toolchains/actions:c_compile",
        "@rules_cc//cc/toolchains/actions:cpp_compile_actions",
    ],
    args = ["--target=x86_64-pc-windows-msvc"],
    tags = ["manual"],
)

cc_args(
    name = "cpp_exceptions",
    actions = ["@rules_cc//cc/toolchains/actions:cpp_compile_actions"],
    args = ["/EHsc"],
)

cc_args(
    name = "windows_sysroot",
    actions = [
        "@rules_cc//cc/toolchains/actions:c_compile",
        "@rules_cc//cc/toolchains/actions:cpp_compile_actions",
    ],
    args = [
        "-Xclang",
        "-internal-isystem",
        "-Xclang",
        "{crt_include}",
        "-Xclang",
        "-internal-isystem",
        "-Xclang",
        "{sdk_include_ucrt}",
        "-Xclang",
        "-internal-isystem",
        "-Xclang",
        "{sdk_include_um}",
        "-Xclang",
        "-internal-isystem",
        "-Xclang",
        "{sdk_include_shared}",
    ],
    data = ["@xwin_sysroot//:includes"],
    format = {
        "crt_include": "@xwin_sysroot//:crt_include",
        "sdk_include_shared": "@xwin_sysroot//:sdk_include_shared",
        "sdk_include_ucrt": "@xwin_sysroot//:sdk_include_ucrt",
        "sdk_include_um": "@xwin_sysroot//:sdk_include_um",
    },
    tags = ["manual"],
)

cc_args(
    name = "machine_x64",
    actions = ["@rules_cc//cc/toolchains/actions:link_actions"],
    args = ["/MACHINE:X64"],
)

cc_args(
    name = "sysroot_libs",
    actions = ["@rules_cc//cc/toolchains/actions:link_actions"],
    args = [
        "/LIBPATH:{crt_lib}",
        "/LIBPATH:{sdk_lib_ucrt}",
        "/LIBPATH:{sdk_lib_um}",
    ],
    data = ["@xwin_sysroot//:libs"],
    format = {
        "crt_lib": "@xwin_sysroot//:crt_lib",
        "sdk_lib_ucrt": "@xwin_sysroot//:sdk_lib_ucrt",
        "sdk_lib_um": "@xwin_sysroot//:sdk_lib_um",
    },
    tags = ["manual"],
)
