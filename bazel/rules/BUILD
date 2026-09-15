load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

# The shared runner behind rust_wine_test() (xcomp/rust_wine_test.bzl).
exports_files(["xcomp/rust-test-wine.sh"])

py_library(
    name = "runpath_patch",
    srcs = ["runpath_patch.py"],
    imports = ["."],
)

py_binary(
    name = "set_runpath_tree",
    srcs = ["set_runpath_tree.py"],
    visibility = ["//visibility:public"],
    deps = [":runpath_patch"],
)

py_binary(
    name = "set_runpath_whl",
    srcs = ["set_runpath_whl.py"],
    visibility = ["//visibility:public"],
    deps = [":runpath_patch"],
)

py_binary(
    name = "console_scripts_gen",
    srcs = ["console_scripts_gen.py"],
    visibility = ["//visibility:public"],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = ["console_scripts_gen_test.py"] + glob(["tests/*.py"]),
    imports = ["."],
    deps = [
        ":console_scripts_gen",
        ":set_runpath_tree",
        ":set_runpath_whl",
    ],
)
