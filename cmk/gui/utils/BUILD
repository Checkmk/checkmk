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
            "html.py",
            "htpasswd.py",
            "json.py",
            "misc.py",
            "permission_verification.py",
            "request_context.py",
            "security_log_events.py",
            "selection_id.py",
            "sort.py",
            "speaklater.py",
            "temperate_unit.py",
            "time.py",
            "transaction_manager.py",
        ],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
