load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

exports_files(["generate_api_spec.py"])

py_library(
    name = "spec_generator",
    srcs = [
        "_code_examples.py",
        "_doc_marshmallow.py",
        "_doc_pydantic.py",
        "_doc_utils.py",
        "_type_defs.py",
    ],
    imports = ["../../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:http",
        "//cmk/gui:permissions",
        "//cmk/gui/openapi:openapi_init",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/framework:core",
        "//cmk/gui/openapi/restful_objects",
        "//cmk/gui/openapi/restful_objects:type_defs",
        "//cmk/gui/openapi/restful_objects:versioned_endpoint_map",
        "//cmk/gui/openapi/spec",
        "//cmk/gui/openapi/spec:utils",
        "//cmk/gui/utils:permission_verification",
        requirement("apispec"),
        requirement("jinja2"),
        requirement("marshmallow"),
        requirement("pydantic"),
        requirement("werkzeug"),
    ],
)

py_binary(
    name = "generate_api_spec",
    srcs = ["generate_api_spec.py"],
    main = "generate_api_spec.py",
    visibility = ["//:__subpackages__"],
    deps = select({
        "@cmk//edition:cloud": [
            "//cmk/editions:community",
            "//cmk/editions/nonfree:cloud",
            "//cmk/editions/nonfree:pro",
            "//cmk/editions/nonfree:ultimate",
        ],
        "@cmk//edition:community": [
            "//cmk/editions:community",
        ],
        "@cmk//edition:pro": [
            "//cmk/editions:community",
            "//cmk/editions/nonfree:pro",
        ],
        "@cmk//edition:ultimate": [
            "//cmk/editions:community",
            "//cmk/editions/nonfree:pro",
            "//cmk/editions/nonfree:ultimate",
        ],
        "@cmk//edition:ultimatemt": [
            "//cmk/editions:community",
            "//cmk/editions/nonfree:pro",
            "//cmk/editions/nonfree:ultimate",
            "//cmk/editions/nonfree:ultimatemt",
        ],
    }) + [
        requirement("pyyaml"),
    ],
)

py_binary(
    name = "generate_api_spec_all_editions",
    srcs = ["generate_api_spec.py"],
    main = "generate_api_spec.py",
    visibility = ["//:__subpackages__"],
    deps = select({
        "@//:gpl+nonfree_repo": [
            "//cmk/editions:community",
            "//cmk/editions/nonfree:pro",
        ],
        "@//:gpl_repo": [
            "//cmk/editions:community",
        ],
    }) + [
        requirement("pyyaml"),
    ],
)

# Temporary: spec_generator files that still belong to the monolithic //cmk/gui target.
# _core.py needs cmk.gui.main_modules and cmk.gui.script_helpers (monolithic).
filegroup(
    name = "gui_srcs",
    srcs = [
        "__init__.py",
        "_core.py",
    ],
    visibility = ["//cmk/gui:__pkg__"],
)
