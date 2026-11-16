load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "agents",
    srcs = ["mk_jolokia.py"],
    # Only tests use the agent plug-ins as Python code, see //cmk/plugins:plugins.
    # The jolokia special agent is the exception: it imports mk_jolokia in the site.
    visibility = [
        "//cmk/plugins:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        requirement("requests"),
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
