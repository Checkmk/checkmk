load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "agents",
    srcs = [
        "plesk_backups.py",
        "plesk_domains.py",
    ],
    visibility = [
        "//cmk/plugins:__subpackages__",
        "//tests:__subpackages__",
    ],
)
