load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "data_source",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/data_source"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui/data_source",
        "//tests:rest_api_client",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
    ],
)
