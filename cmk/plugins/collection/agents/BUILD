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

exports_files(
    ["iis_app_pool_state.ps1"],
    visibility = ["//agents/windows/plugins:__pkg__"],
)
