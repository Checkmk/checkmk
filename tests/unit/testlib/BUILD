load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
        # pytest-xdist for `--numprocesses=NPROC`
        requirement("pytest-xdist"),
    ],
)

py_test(
    name = "testlib",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
        "--random-order-bucket=global",
        "--dist=loadfile",
        "--numprocesses=4",
    ],
    data = ["@//:pyproject.toml"],
    main = ":__test__.py",
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        "//tests/testlib:testlib_system_level",
        requirement("docker"),
        requirement("pytest"),
        requirement("pytest-random-order"),
    ],
)
