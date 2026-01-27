load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@cmk_requirements//:requirements.bzl", "requirement")

filegroup(
    name = "srcs",
    srcs = glob(
        include = ["*"],
        exclude = [
            "__init__.py",
            "BUILD",
            "OWNERS",
            ".f12",
            "Makefile",
        ],
    ),
    visibility = ["//visibility:public"],
)

py_binary(
    # Shares code with `agent_jolokia` in the site.
    name = "apache_status",
    srcs = ["apache_status.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_binary(
    # Shares code with `agent_jolokia` in the site.
    name = "mk_jolokia",
    srcs = ["mk_jolokia.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        requirement("requests"),
        requirement("simplejson"),
    ],
)

py_binary(
    # Shares code with `agent_jolokia` in the site.
    name = "nginx_status",
    srcs = ["nginx_status.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)
