load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "bi",
    srcs = glob(["**/*.py"]),
    args = [
        "--import-mode=importlib",
        "tests/unit/cmk/gui/bi",
    ],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/bi",
        "//cmk/gui:exceptions",
        "//cmk/gui/bi",
        "//packages/cmk-ccc:hostaddress",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
    ],
)
