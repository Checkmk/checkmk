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
        "//cmk/gui:app",
        "//cmk/gui:config",
        "//cmk/gui:session_context",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client",
    ],
)
