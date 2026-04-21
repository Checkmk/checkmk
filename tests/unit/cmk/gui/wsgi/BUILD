load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "wsgi",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/wsgi"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:hooks",
        "//cmk/gui:http",
        "//cmk/gui:pages",
        "//cmk/gui/wsgi",
        "//tests/testlib/gui",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("flask"),
        requirement("pytest"),
    ],
)
