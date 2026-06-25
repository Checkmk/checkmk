load("@aspect_rules_py//py:defs.bzl", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_cmk_test(
    name = "community",
    size = "small",
    timeout = "moderate",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--random-order-bucket=global",
    ],
    main = ":__test__.py",
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        # Do not adjust the dependencies here.
        # These tests test the scope of the edition.
        # Trimming these dependencies to a minimum defeats the purpose.
        "//cmk/editions:community",
        requirement("pytest-random-order"),
    ],
)
