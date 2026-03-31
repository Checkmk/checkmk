load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "agent-plugin-unit",
    # https://bazel.build/reference/be/common-definitions#test.size
    size = "small",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
        "--random-order-bucket=global",
        "--dist=loadfile",
        "--numprocesses=4",
    ],
    data = ["@//:pyproject.toml"] + glob(["datasets/**"]),
    main = ":__test__.py",
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        # pytest-xdist for `--numprocesses=NPROC`
        requirement("pytest-xdist"),
        requirement("pytest-mock"),
        requirement("pytest-asyncio"),
        requirement("pytest-random-order"),
        requirement("pymongo"),
        requirement("marshmallow"),
        "//agents/plugins:agent-plugins-python",
    ],
)
