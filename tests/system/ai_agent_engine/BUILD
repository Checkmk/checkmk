load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "ai_agent_engine",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    deps = [
        requirement("pytest"),
        requirement("requests"),
        "//tests/system:pkg_marker",
        "//tests/testlib",
        "//tests/testlib/common:utils",
    ],
)
