"""Test that a cross-compiled Windows binary statically links the CRT."""

load("@rules_shell//shell:sh_test.bzl", "sh_test")

def _static_crt_test_impl(name, visibility, binary):
    sh_test(
        name = name,
        size = "small",
        srcs = ["//bazel/testing:static_crt_test.sh"],
        args = [
            "$(rlocationpath @llvm_toolchain//:llvm-readobj)",
            "$(rlocationpath {})".format(binary),
        ],
        data = [
            binary,
            "@llvm_toolchain//:llvm-readobj",
        ],
        tags = ["manual"],
        visibility = visibility,
    )

static_crt_test = macro(
    doc = "Fails if `binary` (a PE32+ executable) imports any CRT DLL.",
    implementation = _static_crt_test_impl,
    attrs = {
        "binary": attr.label(
            doc = "Label of the cross-compiled Windows binary to check.",
            mandatory = True,
            configurable = False,
        ),
    },
)
