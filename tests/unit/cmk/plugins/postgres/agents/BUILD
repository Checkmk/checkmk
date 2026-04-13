load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "agents",
    # https://bazel.build/reference/be/common-definitions#test.size
    size = "small",
    srcs = [
        "__test__.py",
        "test_mk_postgres.py",
    ],
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
    ],
    data = ["@//:pyproject.toml"],
    main = ":__test__.py",
    tags = ["legacy-python"],
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        requirement("marshmallow"),
        requirement("pytest"),
        "//cmk/plugins/postgres/agents",
    ],
)
