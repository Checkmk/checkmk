load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "product_usage",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/product_usage"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
        "//cmk/gui:pages",
        "//cmk/gui/product_usage_analytics",
        "//cmk/product_usage",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)
