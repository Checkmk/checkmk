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

py_library(
    name = "registries",
    srcs = [
        "automation_commands.py",
        "main_menu.py",
        "mode/__init__.py",
        "mode/_base.py",
        "mode/_helpers.py",
        "mode/_registry.py",
        "mode_permissions.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:breadcrumb",
        "//cmk/gui:config",
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:logged_in",
        "//cmk/gui:main_menu",
        "//cmk/gui:page_menu",
        "//cmk/gui:type_defs",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/utils:loading_transition",
        "//cmk/gui/utils:speaklater",
        "//cmk/gui/utils:transaction_manager",
        "//cmk/gui/utils:urls",
        "//cmk/utils",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:resulttype",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:version",
        "//packages/cmk-licensing",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "password_store",
    srcs = ["password_store.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":config_infra",
        "//cmk/gui:hooks",
        "//cmk/gui:i18n",
        "//cmk/gui:logged_in",
        "//cmk/gui:type_defs",
        "//cmk/gui/userdb",
        "//cmk/gui/valuespec",
        "//cmk/utils",
        "//packages/cmk-ccc:store",
    ],
)

py_library(
    name = "groups_io",
    srcs = ["groups_io.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":config_infra",
        "//cmk/gui:groups",
        "//cmk/gui:hooks",
        "//cmk/gui:sites",
    ],
)

py_library(
    name = "passwords",
    srcs = ["passwords.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":config_infra",
        ":groups_io",
        ":password_store",
        "//cmk/gui:exceptions",
        "//cmk/gui:i18n",
        "//cmk/gui:logged_in",
        "//cmk/gui/userdb",
        "//cmk/utils",
        "//packages/cmk-ccc:user",
    ],
)

py_library(
    name = "tag_config_file",
    srcs = ["tag_config_file.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":config_infra",
        "//cmk/gui:hooks",
        "//cmk/utils",
        "//packages/cmk-ccc:store",
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
            "automation_commands.py",
            "changes.py",
            "config_domain_name.py",
            "git.py",
            "groups_io.py",
            "main_menu.py",
            "mode/__init__.py",
            "mode/_base.py",
            "mode/_helpers.py",
            "mode/_registry.py",
            "mode_permissions.py",
            "objref.py",
            "password_store.py",
            "passwords.py",
            "paths.py",
            "sidebar_reload.py",
            "simple_config_file.py",
            "site_changes.py",
            "tag_config_file.py",
            "utils.py",
        ],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
