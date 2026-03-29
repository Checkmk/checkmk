load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "valuespec",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-dcd:__pkg__",
        "//non-free/packages/cmk-liveproxyd:__pkg__",
        "//non-free/packages/cmk-otel-collector:__pkg__",
        "//non-free/packages/cmk-robotmk:__pkg__",
        "//omd/packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:framework",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
        requirement("python-dateutil"),
    ],
)
