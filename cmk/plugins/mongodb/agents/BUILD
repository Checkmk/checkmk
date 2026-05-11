load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "agents",
    srcs = ["mk_mongodb.py"],
    visibility = [
        "//cmk/plugins:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        requirement("pymongo"),
    ],
)
