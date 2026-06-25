load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

# Owns __init__.py so the source-presence check finds it without putting it in
# the py_test's srcs (which would mis-anchor pytest's package discovery,
# especially given the no-sandbox tag below).
py_library(
    name = "pkg",
    testonly = True,
    srcs = ["__init__.py"],
)

py_cmk_test(
    name = "change_quality",
    size = "small",
    srcs = [
        "test_components.py",
        "test_detect_test.py",
        "test_repo.py",
        "test_rows.py",
        "test_state.py",
        "test_walk.py",
    ],
    # importlib import mode: yields proper module-name nodeids in JUnit XML
    # instead of bazel-out runfiles paths (the no-sandbox tag below makes
    # pytest's default `prepend` mode anchor on the runfiles tree).
    # test_walk.py shells out to git; depend on the host git binary by
    # opting out of the bazel sandbox (same pattern as tests/code_quality/werks).
    imports = ["../../../.."],
    pytest_main = True,
    tags = ["no-sandbox"],
    use_project_pytest_config = True,
    deps = [
        # marshmallow is referenced by the workspace pyproject.toml's
        # filterwarnings list; pytest needs it importable to parse config.
        requirement("marshmallow"),
        requirement("pytest"),
        "//tests/qa_metrics/change_quality",
        "//tests/unit/qa_metrics",
    ],
)
