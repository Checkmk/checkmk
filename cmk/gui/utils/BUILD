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
    name = "temperate_unit",
    srcs = ["temperate_unit.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:i18n",
    ],
)

py_library(
    name = "permission_verification",
    srcs = ["permission_verification.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
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
        "//cmk/gui:type_defs",
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
    deps = [
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
    ],
)

py_library(
    name = "transaction_manager",
    srcs = ["transaction_manager.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:ctx_stack",
        "//cmk/gui:http",
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
        "//tests:__subpackages__",
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
        "//cmk/gui:i18n",
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
        "//cmk/gui:num_split",
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
        "//cmk/utils",
        "//packages/cmk-ccc:version",
    ],
)

py_library(
    name = "output_funnel",
    srcs = ["output_funnel.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:ctx_stack",
        requirement("flask"),
    ],
)

py_library(
    name = "user_errors",
    srcs = ["user_errors.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:ctx_stack",
        "//cmk/gui:exceptions",
    ],
)

py_library(
    name = "escaping",
    srcs = ["escaping.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":html",
        ":speaklater",
        "//cmk/utils",
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
    deps = [
        "//cmk/gui:hooks",
        "//cmk/gui:http",
    ],
)

py_library(
    name = "timeout_manager",
    srcs = ["timeout_manager.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:ctx_stack",
        "//cmk/gui:exceptions",
        "//cmk/gui:i18n",
    ],
)

py_library(
    name = "language_cookie",
    srcs = ["language_cookie.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:http",
    ],
)

py_library(
    name = "filter",
    srcs = ["filter.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:http",
        "//cmk/gui:type_defs",
    ],
)

py_library(
    name = "product_usage_analytics_popup_cookie",
    srcs = ["product_usage_analytics_popup_cookie.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:http",
        "//packages/cmk-ccc:site",
    ],
)

py_library(
    name = "user_frontend_settings_cookie",
    srcs = ["user_frontend_settings_cookie.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui:http",
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
        "//tests:__subpackages__",
    ],
    deps = [
        ":escaping",
        ":html",
        requirement("flask"),
    ],
)

py_library(
    name = "urls",
    srcs = ["urls.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":escaping",
        ":transaction_manager",
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:type_defs",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
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
        "//cmk/gui:type_defs",
    ],
)

# The remaining utils files are tightly coupled with the monolithic cmk/gui:gui target
# (circular imports). They are exported as a filegroup so gui can include them in its srcs
# as a temporary measure and boiled down by following steps.
filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "agent.py",
            "agent_registration.py",
            "autocompleter_config.py",
            "compatibility.py",
            "dataclasses.py",
            "encrypter.py",
            "escaping.py",
            "filter.py",
            "flashed_messages.py",
            "html.py",
            "htpasswd.py",
            "json.py",
            "language_cookie.py",
            "misc.py",
            "mobile.py",
            "output_funnel.py",
            "permission_verification.py",
            "popups.py",
            "product_usage_analytics_popup_cookie.py",
            "request_context.py",
            "security_log_events.py",
            "selection_id.py",
            "sort.py",
            "speaklater.py",
            "temperate_unit.py",
            "time.py",
            "timeout_manager.py",
            "transaction_manager.py",
            "urls.py",
            "user_errors.py",
            "user_frontend_settings_cookie.py",
        ],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
