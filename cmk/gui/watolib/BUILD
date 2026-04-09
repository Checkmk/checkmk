load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "config_infra",
    srcs = [
        "appendstore.py",
        "audit_log.py",
        "changes.py",
        "config_domain_name.py",
        "git.py",
        "objref.py",
        "paths.py",
        "sidebar_reload.py",
        "simple_config_file.py",
        "site_changes.py",
        "utils.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:ctx_stack",
        "//cmk/gui:exceptions",
        "//cmk/gui:hooks",
        "//cmk/gui:i18n",
        "//cmk/gui:log",
        "//cmk/gui:logged_in",
        "//cmk/gui:site_config",
        "//cmk/gui:type_defs",
        "//cmk/gui:user_sites",
        "//cmk/gui:validation_utils",
        "//cmk/gui/utils:escaping",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:misc",
        "//cmk/gui/utils:speaklater",
        "//cmk/gui/valuespec",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-livestatus-client:py_livestatus",
        requirement("flask"),
        requirement("pydantic"),
    ],
)

# Temporary: watolib files that still belong to the monolithic //cmk/gui target.
# Remove this filegroup once watolib is fully extracted.
filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "appendstore.py",
            "audit_log.py",
            "changes.py",
            "config_domain_name.py",
            "git.py",
            "objref.py",
            "paths.py",
            "sidebar_reload.py",
            "simple_config_file.py",
            "site_changes.py",
            "utils.py",
        ],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
