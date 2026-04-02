load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "scripts_py",
    srcs = ["attach_evidence.py"],
    deps = [requirement("jira")],
)
