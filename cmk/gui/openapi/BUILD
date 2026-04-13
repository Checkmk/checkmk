load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

exports_files([
    ".f12",
    "spec/spec_generator/generate_api_spec.py",
])

py_library(
    name = "utils",
    srcs = ["utils.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:http",
        "//cmk/gui/openapi/restful_objects:type_defs",
        "//cmk/utils",
        requirement("docstring-parser"),
        requirement("werkzeug"),
    ],
)

py_library(
    name = "permission_tracking",
    srcs = ["permission_tracking.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:ctx_stack",
    ],
)

py_library(
    name = "_type_adapter",
    srcs = ["_type_adapter.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        requirement("pydantic"),
    ],
)

py_library(
    name = "openapi_init",
    srcs = [
        "__init__.py",
        "version.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/restful_objects",
    ],
)

py_binary(
    name = "generate_api_spec",
    srcs = ["spec/spec_generator/generate_api_spec.py"],
    main = "spec/spec_generator/generate_api_spec.py",
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

# Variant of generate_api_spec that always includes at least pro edition
# modules. Used to generate the internal OpenAPI spec for TypeScript types
# consumed by cmk-frontend-vue, which ships the same bundle for all editions.
# Limited to community + pro to avoid pulling in ultimate deps that are not
# available in all nonfree edition checkouts (e.g. pro builds strip ultimate/).
py_binary(
    name = "generate_api_spec_all_editions",
    srcs = ["spec/spec_generator/generate_api_spec.py"],
    main = "spec/spec_generator/generate_api_spec.py",
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

# Temporary: openapi files that still belong to the monolithic //cmk/gui target.
# Remove this filegroup once openapi is fully extracted.
filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            # In own targets in this BUILD
            "__init__.py",
            "_type_adapter.py",
            "permission_tracking.py",
            "version.py",
            # In :generate_api_spec / :generate_api_spec_all_editions
            "spec/spec_generator/generate_api_spec.py",
            # In :utils
            "utils.py",
        ],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
