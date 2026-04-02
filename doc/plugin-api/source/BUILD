load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_sphinx//sphinx:defs.bzl", "sphinx_html")

py_binary(
    name = "sphinx_build",
    srcs = ["@rules_sphinx//sphinx/tools:sphinx_build_wrapper.py"],
    main = "sphinx_build_wrapper.py",
    tags = ["no-mypy"],
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
        requirement("sphinx"),
        requirement("sphinx_autodoc_typehints"),
        requirement("sphinx_rtd_theme"),
        requirement("pydantic"),
    ],
)

py_library(
    name = "doc_plugin_api_py",
    srcs = [
        "__init__.py",
        "conf.py",
    ],
    deps = [requirement("sphinx")],
)

filegroup(
    name = "srcs",
    srcs = glob(
        include = ["**/*.rst"],
    ),
)

sphinx_html(
    name = "plugin-api",
    srcs = glob(["_static/**/*"]) + [":srcs"] + select({
        "@cmk//edition:community": [],
        "//conditions:default": ["//doc/plugin-api/source/nonfree/pro"],
    }),
    args = ["--fail-on-warning"],
    config = "conf.py",
    index = "index.rst",
    sphinx_build = ":sphinx_build",
)

alias(
    name = "view",
    actual = ":plugin-api.view",
    visibility = ["//:__subpackages__"],
)

build_test(
    name = "build_test",
    targets = [":plugin-api"],
)

pkg_tar(
    name = "pkg_tar",
    srcs = [
        ":plugin-api",
    ],
    package_dir = "share/doc/check_mk/plugin-api/html",
    stamp = 1,
    strip_prefix = "plugin-api_html",
    visibility = ["//omd:__pkg__"],
)
