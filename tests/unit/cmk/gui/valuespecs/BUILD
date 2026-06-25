load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "valuespecs",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/valuespecs",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/gui/graphing",
        "//cmk/gui/utils:encrypter",
        "//cmk/gui/utils:html",
        "//cmk/gui/valuespec",
        "//packages/cmk-crypto",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("time-machine"),
    ],
)
