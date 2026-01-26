load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_sphinx//sphinx:defs.bzl", "sphinx_html")

py_binary(
    name = "sphinx_build",
    srcs = ["@rules_sphinx//sphinx/tools:sphinx_build_wrapper.py"],
    main = "sphinx_build_wrapper.py",
    tags = ["no-mypy"],
    deps = [
        requirement("sphinx"),
        requirement("sphinx_autodoc_typehints"),
        requirement("sphinx_rtd_theme"),
        requirement("pydantic"),
        "//cmk:cmk_cloud",
        "//cmk:cmk_community",
        "//cmk:cmk_pro",
        "//cmk:cmk_ultimate",
        "//cmk:cmk_ultimatemt",
    ],
)

sphinx_html(
    name = "plugin-api",
    srcs =
        glob(["source/**/*"]),
    args = ["--fail-on-warning"],
    config = "source/conf.py",
    index = "source/index.rst",
    sphinx_build = ":sphinx_build",
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
