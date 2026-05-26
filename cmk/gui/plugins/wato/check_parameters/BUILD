load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:write_file.bzl", "write_file")

# Materializes the directory in this target's runfiles tree without an __init__.py, so Python
# treats it as an implicit namespace package.
# When a target depends on both this stub and the real target, the namespace merges across both
# runfiles paths and the real submodules remain importable.
write_file(
    name = "_namespace_file",
    out = "_namespace_stub/cmk/gui/plugins/wato/check_parameters/_namespace.py",
)

py_library(
    name = "stub",
    srcs = [":_namespace_file"],
    imports = ["_namespace_stub"],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
)

py_library(
    name = "check_parameters",
    srcs = glob(["**/*.py"]),
    imports = ["../../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/form_specs",
        "//cmk/gui/inventory",
        "//cmk/gui/plugins/wato",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:transaction_manager",
        "//cmk/gui/utils:urls",
        "//cmk/gui/valuespec",
        "//cmk/gui/wato",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:password_store",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
    ],
)
