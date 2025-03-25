load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@cmk_requirements//:requirements.bzl", "requirement")

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
