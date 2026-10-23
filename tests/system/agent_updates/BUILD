load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "agent_updates",
    testonly = True,
    srcs = glob(
        include = ["**/*.py"],
    ),
    imports = ["../../.."],
    deps = [
        requirement("pytest"),
        "//tests/system:pkg_marker",
        "//tests/testlib/common",
        "//tests/testlib/system",
    ],
)
