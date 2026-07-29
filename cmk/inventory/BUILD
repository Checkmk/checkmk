load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "inventory",
    srcs = [
        "__init__.py",
        "config.py",
        "paths.py",
        "structured_data.py",
        "transformation/__init__.py",
        "transformation/__main__.py",
        "transformation/main.py",
    ],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-liveproxyd:__pkg__",
        "//packages/cmk-check-engine:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:resulttype",
        "//packages/cmk-ccc:store",
    ],
)
