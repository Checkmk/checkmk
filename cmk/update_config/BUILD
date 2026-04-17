load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "update_config",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "**/community/**",
            "**/nonfree/**",
        ],
    ),
    imports = ["../.."],
    visibility = [
        "//bin:__subpackages__",
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk:message_broker_certs",
        "//cmk:validate_config",
        "//cmk/base:app",
        "//cmk/base:config",
        "//cmk/checkengine",
        "//cmk/gui",
        "//cmk/gui/job_scheduler",
        "//cmk/utils",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-ec",
        "//packages/cmk-mkp-tool",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-werks",
        requirement("python-dateutil"),
    ],
)
