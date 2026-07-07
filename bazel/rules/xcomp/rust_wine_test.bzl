"""Wine test tier for cross-compiled Rust test binaries."""

load("@rules_shell//shell:sh_test.bzl", "sh_test")

def _rust_wine_test_impl(
        name,
        visibility,
        binaries,
        skip_file,
        prepare,
        prepare_args,
        data,
        size,
        tags):
    args = [
        "$(rootpath @wine_linux_x86_64//:wine_bin)",
        "$(rootpath %s)" % skip_file,
    ]
    hook = []
    if prepare:
        args += ["$(rootpath %s)" % prepare] + prepare_args
        hook = [prepare]
    args += ["--"] + ["$(rootpath %s)" % b for b in binaries]
    sh_test(
        name = name,
        size = size,
        srcs = ["//bazel/rules:xcomp/rust-test-wine.sh"],
        args = args,
        data = [
            skip_file,
            "@wine_linux_x86_64//:wine",
            "@wine_linux_x86_64//:wine_bin",
        ] + binaries + hook + data,
        tags = ["manual"] + tags,
        visibility = visibility,
    )

rust_wine_test = macro(
    doc = "Runs cross-compiled Rust libtest binaries under the pinned Wine.",
    implementation = _rust_wine_test_impl,
    attrs = {
        "binaries": attr.label_list(
            doc = "Labels of the Windows test executables, run in order.",
            mandatory = True,
            configurable = False,
        ),
        "data": attr.label_list(
            doc = "Extra runfiles (hook inputs such as fixtures or binaries).",
            configurable = False,
        ),
        "prepare": attr.label(
            doc = "Optional hook script run before the binaries, from the " +
                  "test cwd (so $(rootpath) arguments resolve) with $WINE " +
                  "and $SCRATCH exported.",
            allow_single_file = True,
            configurable = False,
        ),
        "prepare_args": attr.string_list(
            doc = "Arguments for the prepare hook; use $(rootpath ...) and " +
                  "list the referenced targets in data.",
            configurable = False,
        ),
        "size": attr.string(
            doc = "Test size; the default fits the current tiers.",
            default = "medium",
            configurable = False,
        ),
        "skip_file": attr.label(
            doc = "File listing one libtest --skip substring per line.",
            mandatory = True,
            allow_single_file = True,
            configurable = False,
        ),
        "tags": attr.string_list(
            doc = "Extra tags; manual is always set (windows artifacts must " +
                  "not build in wildcard invocations).",
            configurable = False,
        ),
    },
)
