load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_test")

py_test(
    name = "test_localization",
    srcs = ["test_localization.py"],
    deps = [
        "//tests/astrein:checker_localization",
        requirement("pytest"),
    ],
)

py_test(
    name = "test_module_layers",
    srcs = ["test_module_layers.py"],
    deps = [
        "//tests/astrein:checker_module_layers",
        requirement("pytest"),
    ],
)
