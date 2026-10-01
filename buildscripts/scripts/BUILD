load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_binary(
    name = "check_thirdparty_modules",
    srcs = ["check_thirdparty_modules.py"],
)

py_binary(
    name = "collect_rust_tests",
    srcs = ["collect_rust_tests.py"],
    main = "collect_rust_tests.py",
    tags = ["manual"],
)

py_pytest_main(
    name = "__unit_test__",
    deps = [requirement("pytest")],
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/*.py"]) + [":__unit_test__.py"],
    imports = ["."],
    main = "__unit_test__.py",
    deps = [
        ":__unit_test__",
        ":check_thirdparty_modules",
        requirement("pytest"),
    ],
)
