load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "agents",
    srcs = [
        "apache_status.py",
        "isc_dhcpd.py",
    ],
    visibility = [
        "//cmk/plugins:__subpackages__",
        "//tests:__subpackages__",
    ],
)
