load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

# What auth.py needs to verify an OAuth bearer token on an incoming REST API
# request. Kept separate from the "oauth" target below (the RFC 6749 HTTP
# endpoints, WATO client management, and their own dependencies) so that
# low-level, foundational callers like cmk.gui.auth don't transitively carry
# the page layer's dependencies -- and so the page layer stays free to depend
# on more things over time without risking a cycle back through cmk.gui.auth,
# which this target itself is a dependency of.
py_library(
    name = "token_verification",
    srcs = ["__init__.py"] + glob(["token/**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/gui:scopes",
        "//cmk/gui/userdb",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:resulttype",
        "//packages/cmk-ccc:user",
    ],
)

py_library(
    name = "oauth",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "__init__.py",
            "token/**",
        ],
    ),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":token_verification",
        "//packages/cmk-web/cmk/web/utils",
        requirement("pydantic"),
        requirement("redis"),
        "//cmk/gui:core_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui:scopes",
        "//cmk/gui/utils",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/utils:redis",
        "//packages/cmk-ccc:site",
    ],
)
