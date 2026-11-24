load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_sphinx//sphinx:defs.bzl", "sphinx_html")
load(":defs.bzl", "doc_srcs")

py_binary(
    name = "sphinx_build",
    srcs = ["@rules_sphinx//sphinx/tools:sphinx_build_wrapper.py"],
    data = ["@plantuml"],
    main = "sphinx_build_wrapper.py",
    tags = [
        "no-deballast",  # deps are imported at runtime by sphinx autodoc, not in srcs
        "no-mypy",
    ],
    deps = [
        "//packages/cmk-check-engine/cmk/checkengine/parser",
        requirement("sphinx"),
        requirement("sphinx_autodoc_typehints"),
        requirement("sphinx_rtd_theme"),
        requirement("sphinxcontrib_plantuml"),
        requirement("sphinxcontrib_spelling"),
    ],
)

doc_srcs(
    name = "srcs",
    srcs = glob([
        "**/*.puml",
        "**/*.rst",
        "**/*.svg",
    ]) + [
        # Pages that live in the package they describe
        "//omd/packages/omd:docs",
        "//packages/cmk-backup:docs",
        "//packages/cmk-check-engine:docs",
        "//packages/cmk-livestatus-client:docs",
        "//packages/cmk-maps:docs",
        "//packages/cmk-plugins/cmk/plugins/kube:docs",
    ] + select({
        "@cmk//edition:community": [],
        "//conditions:default": [
            "//non-free/packages/cmk-data-backend:docs",
            "//non-free/packages/cmk-liveproxyd:docs",
            "//non-free/packages/cmk-mknotifyd:docs",
            "//non-free/packages/cmk-relay-engine:docs",
        ],
    }),
    visibility = ["//:__subpackages__"],
)

# Only needed to build the HTML, so not part of :srcs, which omd ships.
filegroup(
    name = "templates",
    srcs = glob(["_templates/*.html"]),
)

sphinx_html(
    name = "documentation",
    srcs = [
        ":srcs",
        ":templates",
    ],
    config = "conf.py",
    index = "index.rst",
    sphinx_build = ":sphinx_build",
    visibility = ["//visibility:public"],
)

py_library(
    name = "doc_documentation_py",
    srcs = [
        "__init__.py",
        "conf.py",
    ],
)

build_test(
    name = "build_test",
    targets = [":documentation"],
)
