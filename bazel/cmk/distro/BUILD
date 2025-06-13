load("@bazel_skylib//lib:selects.bzl", "selects")
load("@bazel_skylib//rules:common_settings.bzl", "string_flag")

package(default_visibility = ["//visibility:public"])

string_flag(
    name = "distro",
    build_setting_default = "UNSET",
    values = [
        "almalinux-8",
        "almalinux-9",
        "cma-4",
        "debian-11",
        "debian-12",
        "sles-15sp3",
        "sles-15sp4",
        "sles-15sp5",
        "sles-15sp6",
        "ubuntu-22.04",
        "ubuntu-24.04",
    ],
)

config_setting(
    name = "almalinux_8",
    flag_values = {":distro": "almalinux-8"},
)

config_setting(
    name = "almalinux_9",
    flag_values = {":distro": "almalinux-9"},
)

selects.config_setting_group(
    name = "almalinux",
    match_any = [
        ":almalinux_8",
        ":almalinux_9",
    ],
)

config_setting(
    name = "cma_4",
    flag_values = {":distro": "cma-4"},
)

selects.config_setting_group(
    name = "cma",
    match_any = [":cma_4"],
)

config_setting(
    name = "debian_11",
    flag_values = {":distro": "debian-11"},
)

config_setting(
    name = "debian_12",
    flag_values = {":distro": "debian-12"},
)

selects.config_setting_group(
    name = "debian",
    match_any = [
        ":debian_11",
        ":debian_12",
    ],
)

config_setting(
    name = "sles_15sp3",
    flag_values = {":distro": "sles-15sp3"},
)

config_setting(
    name = "sles_15sp4",
    flag_values = {":distro": "sles-15sp4"},
)

config_setting(
    name = "sles_15sp5",
    flag_values = {":distro": "sles-15sp5"},
)

config_setting(
    name = "sles_15sp6",
    flag_values = {":distro": "sles-15sp6"},
)

selects.config_setting_group(
    name = "sles",
    match_any = [
        ":sles_15sp3",
        ":sles_15sp4",
        ":sles_15sp5",
        ":sles_15sp6",
    ],
)

config_setting(
    name = "ubuntu_22.04",
    flag_values = {":distro": "ubuntu-22.04"},
)

config_setting(
    name = "ubuntu_24.04",
    flag_values = {":distro": "ubuntu-24.04"},
)

selects.config_setting_group(
    name = "ubuntu",
    match_any = [
        ":ubuntu_22.04",
        ":ubuntu_24.04",
    ],
)
