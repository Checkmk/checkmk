load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "index",
    srcs = ["index.py"],
    imports = ["../../.."],
    visibility = [
        "//bin:__pkg__",
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/utils:paths",
        "//packages/cmk-ccc:store",
    ],
)

py_library(
    name = "matchers",
    srcs = ["matchers.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/utils",
        "//cmk/gui/utils:middle",
    ],
)

py_library(
    name = "permissions",
    srcs = ["permissions.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:page_toolkit",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "_routing",
    srcs = ["_routing.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk/gui/search:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":matchers",
        ":permissions",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "quicksearch",
    srcs = ["quicksearch.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/search/_engines:_livestatus",
    ],
)

py_library(
    name = "search",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "index.py",
            "matchers.py",
            "permissions.py",
            "quicksearch.py",
            "_routing.py",
        ],
    ),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":matchers",
        ":permissions",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/background_job/job",
        "//cmk/gui/search/_engines:_livestatus",
        "//cmk/gui/search/_engines:_redis",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)
