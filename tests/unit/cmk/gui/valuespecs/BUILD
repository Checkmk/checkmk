load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "valuespecs",
    srcs = glob(["**/*.py"]),
    args = [
        "--import-mode=importlib",
        "tests/unit/cmk/gui/valuespecs",
    ],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
        "//cmk/gui:type_defs",
        "//cmk/gui/graphing",
        "//cmk/gui/utils:encrypter",
        "//cmk/gui/utils:html",
        "//cmk/gui/valuespec",
        "//packages/cmk-crypto",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
        requirement("time-machine"),
    ],
)
