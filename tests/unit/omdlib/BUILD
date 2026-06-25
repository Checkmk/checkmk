load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "omdlib",
    size = "small",
    srcs = glob(["**/*.py"]),
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//omd/packages/omd:omdlib",
        requirement("pytest-mock"),
        requirement("cryptography"),
    ],
)
