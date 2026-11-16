load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "agents",
    srcs = ["nginx_status.py"],
    # Only tests use the agent plug-ins as Python code, see //cmk/plugins:plugins.
    visibility = ["//tests:__subpackages__"],
)

filegroup(
    name = "files",
    srcs = glob(
        ["*"],
        exclude = ["BUILD"],
    ),
    visibility = ["//cmk/plugins:__pkg__"],
)
