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
