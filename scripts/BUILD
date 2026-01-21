load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@cmk_requirements//:requirements.bzl", "requirement")

exports_files(["requirements.in"])

py_binary(
    name = "sarif_preparse",
    srcs = ["sarif_preparse.py"],
    main = "sarif_preparse.py",
    tags = ["manual"],
    deps = [requirement("sarif-tools")],
)

py_binary(
    name = "collect_mypy",
    srcs = ["collect_mypy.py"],
    main = "collect_mypy.py",
    tags = ["manual"],
)
