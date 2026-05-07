load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_test(
    name = "auth_token",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/auth_token"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        "//cmk/gui/token_auth",
        "//packages/cmk-ccc:user",
        requirement("pytest"),
        requirement("python-dateutil"),
    ],
)
