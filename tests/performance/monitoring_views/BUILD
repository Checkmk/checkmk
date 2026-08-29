load("@aspect_rules_py//py:defs.bzl", "py_library")

package(default_visibility = ["//tests:__subpackages__"])

# The fake Livestatus fleet on its own, so the suites that drive a real site can serve the same
# generated estate over TCP without pulling in the in-process GUI fixtures.
py_library(
    name = "livestatus_fake",
    testonly = True,
    srcs = [
        "__init__.py",
        "livestatus_fake.py",
        "remotes.py",
        "report.py",
        "scenarios.py",
    ],
    imports = ["../../.."],
    deps = [
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client:livestatus-api",
        "//packages/cmk-livestatus-client:py_livestatus",
    ],
)
