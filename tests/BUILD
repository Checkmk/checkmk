load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_py//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "testlib",
    testonly = True,
    srcs = glob(
        include = ["testlib/**"],
        exclude = ["testlib/cse/**"],
    ) + ["__init__.py"],
    imports = [".."],
    deps = [
        "//cmk:lib_cmk",
        requirement("cryptography"),
        requirement("docker"),
        requirement("dockerpty"),
        requirement("pexpect"),
        requirement("playwright"),
        requirement("pytest"),
        requirement("requests"),
    ],
)

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    deps = [
        ":testlib",
        requirement("playwright"),
        requirement("pytest"),
        requirement("pytest-check"),
        requirement("pytest-metadata"),
    ],
)
