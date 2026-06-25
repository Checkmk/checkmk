load("@aspect_rules_py//py:defs.bzl", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
        # pytest-xdist for `--numprocesses=NPROC`
        requirement("pytest-xdist"),
    ],
)

py_cmk_test(
    name = "testlib",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--random-order-bucket=global",
        "--dist=loadfile",
        "--numprocesses=4",
    ],
    main = ":__test__.py",
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        "//tests/testlib:testlib_system_level",
        requirement("docker"),
        requirement("pytest"),
        requirement("pytest-random-order"),
    ],
)
