load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "maps",
    testonly = True,
    srcs = glob(
        include = ["**/*.py"],
    ),
    imports = ["../../.."],
    deps = [
        requirement("playwright"),
        requirement("pytest"),
        requirement("pytest_playwright"),
        # The browser fixtures and the page-object base still live in the GUI
        # suite, which is a holding area being dissolved into feature suites.
        "//tests/system/gui",
        "//tests/system:pkg_marker",
        "//tests/testlib/common",
        "//tests/testlib/pytest_helpers",
        "//tests/testlib/system",
    ],
)
