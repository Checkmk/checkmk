load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "update",
    testonly = True,
    srcs = glob(
        ["**/*.py"],
        exclude = [
            "helpers.py",
            "pytest_plugin.py",
        ],
    ),
    imports = ["../../.."],
    deps = [
        ":helpers",
        requirement("pytest"),
        "//tests/testlib/common",
        "//tests/testlib/pytest_helpers",
        "//tests/testlib/system",
    ],
)

# Shared with the non-free update tests below non-free/tests/system/update/.
# Holds no conftest: both suites have one with the module name
# tests.system.update.conftest.
py_library(
    name = "helpers",
    testonly = True,
    srcs = [
        "helpers.py",
        "pytest_plugin.py",
    ],
    imports = ["../../.."],
    visibility = [
        ":__subpackages__",
        "//non-free/tests/system/update:__subpackages__",
    ],
    deps = [
        requirement("pytest"),
        "//tests/testlib/common",
        "//tests/testlib/system",
    ],
)
