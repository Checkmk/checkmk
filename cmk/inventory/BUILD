load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "inventory",
    srcs = [
        "__init__.py",
        "config.py",
        "paths.py",
        "structured_data.py",
        "transformation/__init__.py",
        "transformation/main.py",
    ],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-liveproxyd:__pkg__",
    ],
    deps = [
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:resulttype",
        "//packages/cmk-ccc:store",
    ],
)

# transformation/__main__.py imports from site-specific packages (cmk.utils.paths, etc.)
# which are not declared as deps of the standalone cmk_inventory library.
# Keep it in a separate target to avoid mypy errors on the library target.
py_library(
    name = "cmk_inventory_main",
    srcs = ["transformation/__main__.py"],
    imports = ["../.."],
    tags = ["no-mypy"],
    visibility = ["//cmk:__pkg__"],
    deps = [":inventory"],
)
