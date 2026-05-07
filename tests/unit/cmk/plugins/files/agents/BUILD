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
    name = "agents",
    size = "small",
    srcs = [
        "__test__.py",
        "test_mk_filestats.py",
    ],
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
    ],
    data = [
        "@//:pyproject.toml",
    ] + glob(["datasets/**"]),
    main = ":__test__.py",
    tags = ["legacy-python"],
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        requirement("marshmallow"),
        requirement("pytest"),
        requirement("pytest-mock"),
        "//cmk/plugins/files/agents",
    ],
)
