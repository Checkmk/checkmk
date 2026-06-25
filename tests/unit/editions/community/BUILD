load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "community",
    size = "small",
    timeout = "moderate",
    srcs = glob(["**/*.py"]),
    args = [
        "--random-order-bucket=global",
    ],
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        # Do not adjust the dependencies here.
        # These tests test the scope of the edition.
        # Trimming these dependencies to a minimum defeats the purpose.
        "//cmk/editions:community",
        requirement("pytest-random-order"),
    ],
)
