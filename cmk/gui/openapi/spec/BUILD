load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

exports_files(["spec_generator/generate_api_spec.py"])

py_library(
    name = "utils",
    srcs = ["utils.py"],
    imports = ["../../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/openapi/framework:core",
        "//cmk/gui/openapi/restful_objects:type_defs",
    ],
)

py_binary(
    name = "generate_api_spec",
    srcs = ["spec_generator/generate_api_spec.py"],
    main = "spec_generator/generate_api_spec.py",
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
    srcs = ["spec_generator/generate_api_spec.py"],
    main = "spec_generator/generate_api_spec.py",
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

# Temporary: spec files that still belong to the monolithic //cmk/gui target.
filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "spec_generator/generate_api_spec.py",
            "utils.py",
        ],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
