load("@rules_cc//cc/toolchains:args.bzl", "cc_args")

package(default_visibility = ["//bazel/toolchains/cc/clang:__subpackages__"])

cc_args(
    name = "compile_defaults",
    actions = [
        "@rules_cc//cc/toolchains/actions:c_compile",
        "@rules_cc//cc/toolchains/actions:cpp_compile_actions",
    ],
    args = [
        "--target=x86_64-pc-windows-msvc",
        # C built via cc (e.g. ring) must not use assert(): it maps to
        # _wassert, which libucrt doesn't provide, and we link the CRT
        # statically.
        "-DNDEBUG",
        # Static CRT. These args reach cargo build scripts as $CFLAGS, where
        # they come after (and thus override) the /MD that cc-rs selects on
        # its own: CARGO_CFG_TARGET_FEATURE under Bazel does not contain
        # crt-static. Objects compiled /MD would emit __imp_* dllimport
        # references that cannot be resolved against the static CRT libs.
        "/MT",
    ],
    tags = ["manual"],
)

# -Xclang -internal-isystem is what clang-cl lowers /imsvc to. It is
# spelled out here because cargo build scripts receive these args via
# $CFLAGS with execroot-relative paths, and rules_rust anchors the paths
# to the execroot only for the GNU-style spellings it knows.
cc_args(
    name = "sysroot_includes",
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
    name = "link_defaults",
    actions = [
        "@rules_cc//cc/toolchains/actions:link_actions",
    ],
    args = [
        "/MACHINE:X64",
        "/LIBPATH:{crt_lib}",
        "/LIBPATH:{sdk_lib_ucrt}",
        "/LIBPATH:{sdk_lib_um}",
        # Force the static CRT variants in and keep the dynamic and debug
        # variants out, so mixed rustc/cc-compiled objects agree on one CRT.
        "/DEFAULTLIB:libucrt.lib",
        "/DEFAULTLIB:libvcruntime.lib",
        "/DEFAULTLIB:libcmt.lib",
        "/NODEFAULTLIB:libvcruntimed.lib",
        "/NODEFAULTLIB:vcruntime.lib",
        "/NODEFAULTLIB:vcruntimed.lib",
        "/NODEFAULTLIB:libcmtd.lib",
        "/NODEFAULTLIB:msvcrt.lib",
        "/NODEFAULTLIB:msvcrtd.lib",
        "/NODEFAULTLIB:ucrt.lib",
        "/NODEFAULTLIB:libucrtd.lib",
        "/NODEFAULTLIB:ucrtd.lib",
    ],
    data = ["@xwin_sysroot//:libs"],
    format = {
        "crt_lib": "@xwin_sysroot//:crt_lib",
        "sdk_lib_ucrt": "@xwin_sysroot//:sdk_lib_ucrt",
        "sdk_lib_um": "@xwin_sysroot//:sdk_lib_um",
    },
    tags = ["manual"],
)
