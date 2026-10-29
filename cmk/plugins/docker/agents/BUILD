load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "agents",
    srcs = ["mk_docker.py"],
    # Only tests use the agent plug-ins as Python code, see //cmk/plugins:plugins.
    visibility = ["//tests:__subpackages__"],
    deps = [
        requirement("docker"),
    ],
)

filegroup(
    name = "files",
    srcs = glob(
        ["*"],
        exclude = ["BUILD"],
    ),
    visibility = ["//cmk/plugins:__pkg__"],
)
