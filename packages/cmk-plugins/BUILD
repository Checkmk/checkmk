load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@rules_shell//shell:sh_library.bzl", "sh_library")
load("//:relay_supported_plugins.bzl", "RELAY_SUPPORTED_PLUGIN_FAMILIES")
load("//bazel/rules:concat_files.bzl", "concat_files")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")

# This detects the plugin families automatically.
# Each subdirectory in cmk/plugins/ is considered a family.
# In most cases it should be sufficient to add the two targets `:<family>` and `:<family>-test`
# Sorting them alphabetically would be nice. Thank you :-)

FAMILIES = [
    d.removeprefix("cmk/plugins/")
    for d in glob(
        ["cmk/plugins/*"],
        exclude_directories = 0,
    )
]

py_library(
    name = "cisco_prime",
    srcs = glob(["cmk/plugins/cisco_prime/**/*.py"]),
    data = glob([
        "cmk/plugins/cisco_prime/checkman/*",
        "cmk/plugins/cisco_prime/libexec/*",
    ]) + ["cmk/plugins/cisco_prime/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
        requirement("requests"),
        requirement("urllib3"),
    ],
)

py_test(
    name = "cisco_prime-test",
    size = "small",
    srcs = glob(["tests/cmk/plugins/cisco_prime/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":cisco_prime",
        requirement("pytest"),
        requirement("responses"),
        requirement("time-machine"),
    ],
)

py_library(
    name = "elasticsearch",
    srcs = glob(["cmk/plugins/elasticsearch/**/*.py"]),
    data = glob([
        "cmk/plugins/elasticsearch/checkman/*",
        "cmk/plugins/elasticsearch/libexec/*",
    ]) + ["cmk/plugins/elasticsearch/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
        requirement("pydantic"),
        requirement("requests"),
        requirement("urllib3"),
    ],
)

py_test(
    name = "elasticsearch-test",
    size = "small",
    srcs = glob(["tests/cmk/plugins/elasticsearch/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":elasticsearch",
        requirement("pytest"),
    ],
)

py_library(
    name = "ipmi",
    srcs = glob([
        "cmk/plugins/ipmi/**/*.py",
    ]),
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
    ],
)

py_test(
    name = "ipmi-test",
    size = "small",
    srcs = glob(["tests/cmk/plugins/ipmi/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":ipmi",
        requirement("pytest"),
    ],
)

py_library(
    name = "kube",
    srcs = glob([
        "cmk/plugins/kube/**/*.py",
    ]),
    data = ["cmk/plugins/kube/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":lib",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
        requirement("kubernetes"),
        requirement("requests"),
    ],
)

py_test(
    name = "kube-test",
    size = "small",
    srcs = glob(["tests/cmk/plugins/kube/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":kube",
        requirement("kubernetes"),
        requirement("polyfactory"),
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("requests"),
    ],
)

py_library(
    name = "lib",
    srcs = glob([
        "cmk/plugins/lib/**/*.py",
    ]),
    data = ["cmk/plugins/lib/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-plugin-apis:agent_based",
    ],
)

py_test(
    name = "lib-test",
    size = "small",
    srcs = glob(["tests/cmk/plugins/lib/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":lib",
        requirement("pytest"),
        requirement("time-machine"),
    ],
)

py_library(
    name = "netapp",
    srcs = glob(["cmk/plugins/netapp/**/*.py"]),
    data = glob([
        "cmk/plugins/netapp/checkman/*",
        "cmk/plugins/netapp/libexec/*",
    ]) + ["cmk/plugins/netapp/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":lib",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
        requirement("netapp_ontap"),
        requirement("pydantic"),
        requirement("urllib3"),
    ],
)

py_test(
    name = "netapp-test",
    size = "small",
    srcs = glob(["tests/cmk/plugins/netapp/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":netapp",
        requirement("polyfactory"),
        requirement("pytest"),
        requirement("time-machine"),
    ],
)

py_library(
    name = "prism",
    srcs = glob(["cmk/plugins/prism/**/*.py"]),
    data = glob([
        "cmk/plugins/prism/checkman/*",
        "cmk/plugins/prism/libexec/*",
    ]) + ["cmk/plugins/prism/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":lib",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
        requirement("requests"),
    ],
)

py_test(
    name = "prism-test",
    size = "small",
    srcs = glob(["tests/cmk/plugins/prism/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":prism",
        requirement("pytest"),
    ],
)

py_library(
    name = "proxmox_ve",
    srcs = glob(["cmk/plugins/proxmox_ve/**/*.py"]),
    data = glob([
        "cmk/plugins/proxmox_ve/checkman/*",
        "cmk/plugins/proxmox_ve/libexec/*",
    ]) + ["cmk/plugins/proxmox_ve/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":lib",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
        requirement("requests"),
        requirement("pydantic"),
    ],
)

py_test(
    name = "proxmox_ve-test",
    size = "small",
    srcs = glob(["tests/cmk/plugins/proxmox_ve/**/*.py"]) + [":__test__.py"],
    data = glob(["tests/cmk/plugins/proxmox_ve/**/files/**"]),
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":proxmox_ve",
        requirement("pytest"),
        requirement("time-machine"),
    ],
)

py_library(
    name = "pure_storage_fa",
    srcs = glob(["cmk/plugins/pure_storage_fa/**/*.py"]),
    data = glob([
        "cmk/plugins/pure_storage_fa/checkman/*",
        "cmk/plugins/pure_storage_fa/libexec/*",
    ]) + ["cmk/plugins/pure_storage_fa/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":lib",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
        requirement("requests"),
        requirement("pydantic"),
        requirement("urllib3"),
    ],
)

py_test(
    name = "pure_storage_fa-test",
    size = "small",
    srcs = glob(["tests/cmk/plugins/pure_storage_fa/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":pure_storage_fa",
        requirement("pytest"),
    ],
)

py_library(
    name = "rabbitmq",
    srcs = glob(["cmk/plugins/rabbitmq/**/*.py"]),
    data = glob([
        "cmk/plugins/rabbitmq/checkman/*",
        "cmk/plugins/rabbitmq/libexec/*",
    ]) + ["cmk/plugins/rabbitmq/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":lib",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
        requirement("requests"),
        requirement("pydantic"),
    ],
)

py_test(
    name = "rabbitmq-test",
    size = "small",
    srcs = glob(["tests/cmk/plugins/rabbitmq/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":rabbitmq",
        requirement("pytest"),
    ],
)

py_library(
    name = "randomds",
    srcs = glob(
        [
            "cmk/plugins/randomds/**/*.py",
        ],
    ),
    data = ["cmk/plugins/randomds/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
    ],
)

py_library(
    name = "redfish",
    srcs = glob(["cmk/plugins/redfish/**/*.py"]),
    data = glob([
        "cmk/plugins/redfish/checkman/*",
        "cmk/plugins/redfish/libexec/*",
    ]) + ["cmk/plugins/redfish/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":lib",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
        requirement("redfish"),
    ],
)

py_test(
    name = "randomds-test",
    size = "small",
    srcs = glob(["tests/cmk/plugins/randomds/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":randomds",
        requirement("pytest"),
    ],
)

py_test(
    name = "redfish-test",
    size = "small",
    srcs = glob(["tests/cmk/plugins/redfish/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":redfish",
        requirement("pytest"),
    ],
)

py_library(
    name = "splunk",
    srcs = glob(["cmk/plugins/splunk/**/*.py"]),
    data = glob([
        "cmk/plugins/splunk/checkman/*",
        "cmk/plugins/splunk/libexec/*",
    ]) + ["cmk/plugins/splunk/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":lib",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
        requirement("requests"),
        requirement("pydantic"),
        requirement("urllib3"),
    ],
)

py_test(
    name = "splunk-test",
    size = "small",
    srcs = glob(["tests/cmk/plugins/splunk/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":splunk",
        requirement("pytest"),
        requirement("polyfactory"),
    ],
)

py_library(
    name = "ucs_bladecenter",
    srcs = glob(["cmk/plugins/ucs_bladecenter/**/*.py"]),
    data = ["cmk/plugins/ucs_bladecenter/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":lib",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
        requirement("defusedxml"),
        requirement("requests"),
        requirement("urllib3"),
    ],
)

py_test(
    name = "ucs_bladecenter-test",
    size = "small",
    srcs = glob(["tests/cmk/plugins/ucs_bladecenter/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":ucs_bladecenter",
        requirement("pytest"),
    ],
)

py_library(
    name = "vsphere",
    srcs = glob(["cmk/plugins/vsphere/**/*.py"]),
    data = glob([
        "cmk/plugins/vsphere/checkman/*",
        "cmk/plugins/vsphere/libexec/*",
    ]) + ["cmk/plugins/vsphere/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":lib",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
        requirement("defusedxml"),
        requirement("python-dateutil"),
        requirement("requests"),
        requirement("urllib3"),
    ],
)

py_test(
    name = "vsphere-test",
    size = "small",
    srcs = glob(["tests/cmk/plugins/vsphere/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":vsphere",
        requirement("pytest"),
        requirement("time-machine"),
    ],
)

#   ____                           _   _                       _
#  / ___| ___ _ __   ___ _ __ __ _| | | |_ __ _ _ __ __ _  ___| |_ ___
# | |  _ / _ \ '_ \ / _ \ '__/ _` | | | __/ _` | '__/ _` |/ _ \ __/ __|
# | |_| |  __/ | | |  __/ | | (_| | | | || (_| | | | (_| |  __/ |_\__ \
#  \____|\___|_| |_|\___|_|  \__,_|_|  \__\__,_|_|  \__, |\___|\__|___/
#                                                   |___/

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
] + [
    "requirements.in-%s" % family
    for family in FAMILIES
])

concat_files(
    name = "requirements.in",
    srcs = [
        ":requirements.in-%s" % family
        for family in FAMILIES
    ],
    visibility = ["//visibility:public"],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [":%s" % family for family in FAMILIES],
    tags = ["no-mypy"],
)

filegroup(
    name = "py_typed",
    srcs = [
        "cmk/plugins/%s/py.typed" % family
        for family in FAMILIES
    ],
)

[filegroup(
    name = "agent-%s" % family,
    srcs = glob(
        ["cmk/plugins/%s/agent/**/*" % family],
        allow_empty = True,
    ),
) for family in FAMILIES]

[filegroup(
    name = "checkman-%s" % family,
    srcs = glob(
        ["cmk/plugins/%s/checkman/**/*" % family],
        allow_empty = True,
    ),
) for family in FAMILIES]

[sh_library(
    name = "libexec-%s" % family,
    srcs = glob(
        ["cmk/plugins/%s/libexec/*" % family],
        allow_empty = True,
    ),
) for family in FAMILIES]

# Here comes the HACK to work around CMK-27714.
# `package_wheel` will not preserve the +x flag
# on the libexec files.
# To fix this we
# * create a dedicated wheel *without* the libexec files
# * add an additional target to contain *just* the libexec files
# * build the pkg_tar from those.
# Once `package_wheel` is fixed, this can be simplified.

[pkg_files(
    name = "libexec-for-pkg_tar-%s" % family,
    srcs = glob(
        ["cmk/plugins/%s/libexec/*" % family],
        allow_empty = True,
    ),
    attributes = pkg_attributes(mode = "0755"),
    prefix = "lib/python%s/site-packages/cmk/plugins/%s/libexec" % (PYTHON_MAJOR_DOT_MINOR, family),
) for family in FAMILIES]

[py_wheel(
    name = "wheel-for-f12-%s" % family,
    distribution = "cmk-plugins-%s-tar" % family,
    entry_points = {
        "cmk.special_agent_supported_on_relay": [
            "%s = %s" % (family, family),
        ] if family in RELAY_SUPPORTED_PLUGIN_FAMILIES else [],
    },
    strip_path_prefixes = ["packages/cmk-plugins"],
    tags = ["manual"],
    version = "1.0.0",
    deps = [
        ":%s" % family,
        ":agent-%s" % family,
        ":checkman-%s" % family,
        ":libexec-%s" % family,
    ],
) for family in FAMILIES]

[py_wheel(
    name = "wheel-for-pkg_tar-%s" % family,
    distribution = "cmk-plugins-%s-tar" % family,
    entry_points = {
        "cmk.special_agent_supported_on_relay": [
            "%s = %s" % (family, family),
        ] if family in RELAY_SUPPORTED_PLUGIN_FAMILIES else [],
    },
    strip_path_prefixes = ["packages/cmk-plugins"],
    version = "1.0.0",
    deps = [
        ":%s" % family,
        ":agent-%s" % family,
        ":checkman-%s" % family,
    ],
) for family in FAMILIES]

[package_wheel(
    name = "pkg_tar-%s" % family,
    additional_files = [":libexec-for-pkg_tar-%s" % family],
    visibility = ["//visibility:public"],
    whl = "wheel-for-pkg_tar-%s" % family,
) for family in FAMILIES]

pkg_tar(
    name = "pkg_tar",
    stamp = 1,
    visibility = ["//visibility:public"],
    deps = [":pkg_tar-%s" % family for family in FAMILIES],
)
