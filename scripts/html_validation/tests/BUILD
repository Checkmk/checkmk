load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "tests",
    size = "small",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    pytest_main = True,
    deps = [
        "//scripts/html_validation",
        requirement("pytest"),
    ],
)
