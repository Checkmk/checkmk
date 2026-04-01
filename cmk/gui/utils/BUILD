load("@aspect_rules_py//py:defs.bzl", "py_library")

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

# The remaining utils files are tightly coupled with the monolithic cmk/gui:gui target
# (circular imports). They are exported as a filegroup so gui can include them in its srcs
# as a temporary measure and boiled down by following steps.
filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "misc.py",
            "permission_verification.py",
            "security_log_events.py",
            "selection_id.py",
            "speaklater.py",
            "temperate_unit.py",
            "transaction_manager.py",
        ],
    ),
    visibility = ["//cmk/gui:__pkg__"],
)
