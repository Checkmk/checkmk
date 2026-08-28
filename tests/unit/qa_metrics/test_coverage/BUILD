load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "tests",
    size = "small",
    srcs = [
        "__init__.py",
        "test_file_lists.py",
        "test_owned_files.py",
        "test_rows.py",
        "test_summary.py",
    ],
    pytest_main = True,
    deps = [
        requirement("pytest"),
        "//tests/qa_metrics/test_coverage",
        "//tests/unit/qa_metrics",
    ],
)
