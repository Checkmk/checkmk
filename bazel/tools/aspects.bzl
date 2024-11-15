load("@rules_mypy//mypy:mypy.bzl", "mypy")

mypy_aspect = mypy(
    mypy_cli = "@@//bazel/tools:mypy_cli",
    mypy_ini = "@@//:pyproject.toml",
    suppression_tags = ["no-mypy"],
)
