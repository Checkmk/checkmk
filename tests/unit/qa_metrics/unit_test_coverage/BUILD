load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "unit_test_coverage",
    size = "small",
    srcs = [
        "__init__.py",
        "test_rows.py",
    ],
    pytest_main = True,
    deps = [
        requirement("pytest"),
        "//tests/qa_metrics/unit_test_coverage",
        "//tests/unit/qa_metrics",
    ],
)
