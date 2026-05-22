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
    name = "validation",
    srcs = ["__test__.py"] + ["test_validate_werks.py"],
    data = [
        "//:defines.make",
        "//.werks",
        "//.werks:werks_config",
    ],
    main = ":__test__.py",
    deps = [
        ":__test__",
        requirement("pytest"),
        "//cmk/utils",
        "//cmk/utils:werks",
        "//packages/cmk-werks",
        "//tests/code_quality:bazel_utils",
    ],
)

py_test(
    name = "werks",
    srcs = ["__test__.py"] + [
        "test_werks.py",
        "test_werks_commands.py",
    ],
    data = [
        "//:defines.make",
        "//.werks",
        "//.werks:werks_config",
    ],
    imports = ["../../.."],
    main = ":__test__.py",
    # This test requires git, however, adding git as a dependency
    # would constantly invalidate the cache, forgoing most advantages
    # of running in Bazel.  Instead, we depend on `//.werks` and run
    # outside of the sandbox.
    tags = [
        "no-sandbox",
        "requires-git",
    ],
    deps = [
        ":__test__",
        requirement("gitpython"),
        requirement("pytest"),
        "//:pyproject-toml",
        "//cmk/utils",
        "//cmk/utils:werks",
        "//packages/cmk-ccc:version",
        "//packages/cmk-werks",
        "//tests/code_quality:bazel_utils",
    ],
)
