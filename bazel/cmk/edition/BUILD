load("@bazel_skylib//rules:common_settings.bzl", "string_flag")

package(default_visibility = ["//visibility:public"])

string_flag(
    name = "edition",
    build_setting_default = "UNSET",
    values = [
        "cre",
        "cce",
        "cee",
        "cme",
        "cse",
    ],
)

config_setting(
    name = "cre",
    flag_values = {":edition": "cre"},
)

config_setting(
    name = "cce",
    flag_values = {":edition": "cce"},
)

config_setting(
    name = "cee",
    flag_values = {":edition": "cee"},
)

config_setting(
    name = "cme",
    flag_values = {":edition": "cme"},
)

config_setting(
    name = "cse",
    flag_values = {":edition": "cse"},
)
