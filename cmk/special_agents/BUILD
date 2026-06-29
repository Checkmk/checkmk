load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "special_agents",
    srcs = glob(["**/*.py"]),
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/utils",
        "//packages/cmk-ccc:crash-reporting",
        "//packages/cmk-ccc:version",
        "//packages/cmk-plugin-apis:server_side_programs",
        requirement("urllib3"),
    ],
)
