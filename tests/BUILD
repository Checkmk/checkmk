load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

exports_files(["dev-requirements.in"])

py_library(
    name = "testlib",
    testonly = True,
    srcs = ["__init__.py"] + glob(
        include = ["testlib/**/*.py"],
    ),
    data = glob(
        include = ["testlib/**"],
        allow_empty = True,
        exclude = ["testlib/**/*.py"],
    ),
    imports = [".."],
    deps = [
        "//cmk:lib_cmk",
        requirement("beautifulsoup4"),
        requirement("clickhouse-connect"),
        requirement("cryptography"),
        requirement("docker"),
        requirement("dockerpty"),
        requirement("fastapi"),
        requirement("pexpect"),
        requirement("playwright"),
        requirement("psutil"),
        requirement("pyjwt"),
        requirement("pyyaml"),
        requirement("pytest"),
        requirement("pytest-check"),
        requirement("requests"),
    ] + select({
        "//:gpl+nonfree_repo": ["//cmk:cmk_cloud"],
        "//:gpl_repo": [],
    }),
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
        include = ["testlib/**/*.py"],
        exclude = ["testlib/unit/**"],
    ),
    data = glob(
        include = ["testlib/**"],
        allow_empty = True,
        exclude = ["testlib/**/*.py"],
    ),
    imports = [".."],
    deps = [
        "//cmk:lib_cmk",
        requirement("beautifulsoup4"),
        requirement("clickhouse-connect"),
        requirement("cryptography"),
        requirement("docker"),
        requirement("dockerpty"),
        requirement("fastapi"),
        requirement("pexpect"),
        requirement("playwright"),
        requirement("psutil"),
        requirement("pyjwt"),
        requirement("pytest"),
        requirement("pytest-check"),
        requirement("pyyaml"),
        requirement("requests"),
    ] + select({
        "//:gpl+nonfree_repo": ["//cmk:cmk_cloud"],
        "//:gpl_repo": [],
    }),
)

py_library(
    name = "testlib_unit",
    testonly = True,
    srcs = ["__init__.py"] + glob(
        include = [
            "testlib/unit/**/*.py",
            "testlib/common/**/*.py",
        ],
    ),
    data = glob(
        include = [
            "testlib/unit/**",
            "testlib/common/**",
        ],
        allow_empty = True,
        exclude = [
            "testlib/unit/**/*.py",
            "testlib/common/**/*.py",
        ],
    ),
    imports = [".."],
    deps = [
        ":testlib",
        "//cmk:lib_cmk",
        requirement("pexpect"),
        requirement("pytest"),
        requirement("pyyaml"),
    ] + select({
        "//:gpl+nonfree_repo": ["//cmk:cmk_pro"],
        "//:gpl_repo": [],
    }),
)
