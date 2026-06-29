load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "speaklater",
    srcs = ["speaklater.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = ["//packages/cmk-web"],
)

py_library(
    name = "misc",
    srcs = ["misc.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
)

py_library(
    name = "images",
    srcs = ["images.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        requirement("pillow"),
    ],
)

py_library(
    name = "temperate_unit",
    srcs = ["temperate_unit.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:core_toolkit",
    ],
)

py_library(
    name = "permission_verification",
    srcs = ["permission_verification.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//tests:__subpackages__",
    ],
)

py_library(
    name = "security_log_events",
    srcs = ["security_log_events.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/utils",
        "//packages/cmk-ccc:user",
    ],
)

py_library(
    name = "selection_id",
    srcs = ["selection_id.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = ["//cmk/gui:core_toolkit"],
)

py_library(
    name = "transaction_manager",
    srcs = ["transaction_manager.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//packages/cmk-backup:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/utils",
        "//packages/cmk-ccc:user",
    ],
)

py_library(
    name = "html",
    srcs = ["html.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//packages/cmk-backup:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-web",
    ],
)

py_library(
    name = "autocompleter_config",
    srcs = ["autocompleter_config.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
)

py_library(
    name = "request_context",
    srcs = ["request_context.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        requirement("flask"),
    ],
)

py_library(
    name = "dataclasses",
    srcs = ["dataclasses.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
)

py_library(
    name = "htpasswd",
    srcs = ["htpasswd.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:user",
        "//packages/cmk-crypto",
    ],
)

py_library(
    name = "encrypter",
    srcs = ["encrypter.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-crypto",
        requirement("flask"),
    ],
)

py_library(
    name = "json",
    srcs = ["json.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/utils",
    ],
)

py_library(
    name = "compatibility",
    srcs = ["compatibility.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:version",
        "//packages/cmk-licensing",
    ],
)

py_library(
    name = "agent_registration",
    srcs = ["agent_registration.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:core_toolkit",
    ],
)

py_library(
    name = "time",
    srcs = ["time.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
)

py_library(
    name = "sort",
    srcs = ["sort.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:core_toolkit",
    ],
)

py_library(
    name = "agent",
    srcs = ["agent.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/utils:paths",
        "//packages/cmk-ccc:version",
    ],
)

py_library(
    name = "output_funnel",
    srcs = ["output_funnel.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//packages/cmk-backup:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:core_toolkit",
        requirement("flask"),
    ],
)

py_library(
    name = "user_errors",
    srcs = ["user_errors.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//packages/cmk-backup:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = ["//cmk/gui:core_toolkit"],
)

py_library(
    name = "escaping",
    srcs = ["escaping.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":html",
        ":speaklater",
        "//cmk/utils",
        "//packages/cmk-web",
    ],
)

py_library(
    name = "mobile",
    srcs = ["mobile.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = ["//cmk/gui:core_toolkit"],
)

py_library(
    name = "timeout_manager",
    srcs = ["timeout_manager.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = ["//cmk/gui:core_toolkit"],
)

py_library(
    name = "filter",
    srcs = ["filter.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = ["//cmk/gui:core_toolkit"],
)

py_library(
    name = "cookies",
    srcs = [
        "language_cookie.py",
        "user_frontend_settings_cookie.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:core_toolkit",
        "//packages/cmk-ccc:site",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "flashed_messages",
    srcs = ["flashed_messages.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//packages/cmk-backup:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":escaping",
        ":html",
        requirement("flask"),
    ],
)

py_library(
    name = "loading_transition",
    srcs = ["loading_transition.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":html",
        ":output_funnel",
        "//cmk/gui:html_toolkit",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "rendering",
    srcs = ["rendering.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":escaping",
        ":html",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/utils",
    ],
)

py_library(
    name = "confirm_with_preview",
    srcs = ["confirm_with_preview.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":html",
        ":mobile",
        ":speaklater",
        ":transaction_manager",
        ":urls",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
    ],
)

py_library(
    name = "urls",
    srcs = ["urls.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//packages/cmk-backup:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":escaping",
        ":transaction_manager",
        "//cmk/gui:core_toolkit",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:version",
        "//packages/cmk-web",
        requirement("flask"),
    ],
)

py_library(
    name = "roles",
    srcs = ["roles.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:user",
    ],
)

py_library(
    name = "regex",
    srcs = ["regex.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":urls",
        "//cmk/gui:auth_core",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
    ],
)

py_library(
    name = "csrf_token",
    srcs = ["csrf_token.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//packages/cmk-backup:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui:core_toolkit",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:user",
        requirement("flask"),
    ],
)

py_library(
    name = "popups",
    srcs = ["popups.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":urls",
        "//cmk/gui:core_toolkit",
    ],
)

py_library(
    name = "labels",
    srcs = ["labels.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client",
    ],
)
