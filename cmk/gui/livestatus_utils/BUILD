load("@aspect_rules_py//py:defs.bzl", "py_library")

# Tiny testing helper.
py_library(
    name = "livestatus_utils",
    testonly = True,
    srcs = [
        "__init__.py",
        "testing.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:script_helpers",
        "//cmk/gui:session",
        "//cmk/gui:sites",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client",
    ],
)
