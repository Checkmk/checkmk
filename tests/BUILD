load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "testlib",
    testonly = True,
    srcs = ["__init__.py"] + glob(include = ["testlib/**"]),
    imports = [".."],
    deps = [
        "//cmk:lib_cmk",
        requirement("beautifulsoup4"),
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

py_library(
    name = "testlib_system_level",
    testonly = True,
    srcs = ["__init__.py"] + glob(
        include = ["testlib/**"],
        exclude = ["testlib/unit/**"],
    ),
    imports = [".."],
    deps = [
        "//cmk:lib_cmk",
        requirement("beautifulsoup4"),
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
    name = "testlib_unit",
    testonly = True,
    srcs = ["__init__.py"] + glob(include = [
        "testlib/unit/**",
        "testlib/common/**",
    ]),
    imports = [".."],
    deps = [
        "//cmk:lib_cmk",
        requirement("pexpect"),
        requirement("pytest"),
    ],
)
