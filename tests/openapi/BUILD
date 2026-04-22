load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "conftest",
    testonly = True,
    srcs = [
        "__init__.py",
        "conftest.py",
    ],
    deps = [
        "//cmk/gui",
        "//cmk/gui:config",
        "//cmk/gui/livestatus_utils",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client:py_livestatus",
        "//tests:fake_site",
        "//tests:rest_api_client",
        "//tests/testlib/common:repo",
        "//tests/testlib/gui",
        requirement("flask"),
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
        requirement("pytest-xdist"),
    ],
)

write_file(
    name = "cannot_fail",
    out = "test_cannot_fail.py",
    content = [
        "def test_cannot_fail() -> None:",
        "    assert True",
    ],
)

py_test(
    name = "smoke",
    size = "small",
    srcs = [
        "__test__.py",
        "test_cannot_fail.py",
    ],
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
    ],
    data = ["@//:pyproject.toml"],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":conftest",
    ],
)

py_test(
    name = "repo_community",
    size = "small",
    timeout = "moderate",
    srcs = [
        "__init__.py",
        "__test__.py",
    ] + glob(include = ["test_*.py"]),
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
        "--random-order-bucket=global",
        "--dist=loadfile",
        "--numprocesses=4",
    ],
    data = ["@//:pyproject.toml"],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":conftest",
        requirement("pytest-random-order"),
    ],
)
