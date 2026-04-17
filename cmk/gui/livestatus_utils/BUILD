load("@aspect_rules_py//py:defs.bzl", "py_library")

# Tiny testing helper. Depends on //cmk/gui for cmk.gui.script_helpers
# (application_and_request_context). Nothing in the monolith imports
# livestatus_utils.testing, so this does not form a cycle.
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
        "//cmk/gui",
        "//cmk/gui:session",
        "//cmk/gui:sites",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client",
    ],
)
