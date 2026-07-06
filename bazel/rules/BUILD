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

py_test(
    # uses `unittest` to avoid overhead.
    name = "console_scripts_gen_test",
    size = "small",
    srcs = ["console_scripts_gen_test.py"],
    imports = ["."],
    main = "console_scripts_gen_test.py",
    deps = [":console_scripts_gen"],
)
