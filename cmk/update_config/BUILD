load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")

# Only for static analysis.
py_binary(
    name = "cmk-update-config",
    srcs = ["cmk-update-config.py"],
    main = "cmk-update-config.py",
    visibility = ["//cmk:__pkg__"],
    deps = [":update_config"],
)

pkg_files(
    name = "cmk-update-config-pkg",
    srcs = ["cmk-update-config.py"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    renames = {"cmk-update-config.py": "cmk-update-config"},
    visibility = [
        "//omd:__pkg__",
    ],
)

py_library(
    name = "update_config",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "**/community/**",
            "**/nonfree/**",
            "cmk-update-config.py",
        ],
    ),
    imports = ["../.."],
    tags = [
        "deballast-keep=//cmk:message_broker_certs",  # exercised by the config-update at runtime, not a static import
    ],
    # TODO: factor out an API such that packages only have to depend on that.
    # restrict visibility for the rest.
    visibility = ["//visibility:public"],
    deps = [
        "//cmk:message_broker_certs",
        "//cmk/base:app",
        "//cmk/base/config",
        "//cmk/checkengine",
        "//cmk/gui:app",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:general_pages",
        "//cmk/gui:messaging",
        "//cmk/gui:page_toolkit",
        "//cmk/gui:request_globals",
        "//cmk/gui:session_context",
        "//cmk/gui/dashboard",
        "//cmk/gui/form_specs",
        "//cmk/gui/graphing",
        "//cmk/gui/job_scheduler",
        "//cmk/gui/pagetypes",
        "//cmk/gui/search:index",
        "//cmk/gui/userdb",
        "//cmk/gui/utils:misc",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:urls",
        "//cmk/gui/views",
        "//cmk/gui/views:components",
        "//cmk/gui/visuals",
        "//cmk/gui/wato",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:groups_io",
        "//cmk/gui/watolib:registries",
        "//cmk/plugins",
        "//cmk/utils",
        "//cmk/utils:redis",
        "//cmk/validate_config",
        "//packages/cmk-backup:gui",
        "//packages/cmk-backup:utils",
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
        "//packages/cmk-check-engine/cmk/checkengine/discovery",
        "//packages/cmk-check-engine/cmk/checkengine/plugin_backend",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-ec",
        "//packages/cmk-mkp-tool",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-werks:site",
        "//packages/cmk-werks:tool",
        "//packages/cmk-wsgi",
        requirement("python-dateutil"),
    ],
)
