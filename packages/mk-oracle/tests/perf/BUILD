load("@aspect_rules_py//py:defs.bzl", "py_binary")

py_library(
    name = "bench-phases_lib",
    srcs = ["bench-phases.py"],
)

py_binary(
    name = "bench-phases",
    srcs = [":bench-phases_lib"],
    tags = ["manual"],
)

py_library(
    name = "measure_lib",
    srcs = ["measure.py"],
)

py_binary(
    name = "measure",
    srcs = [":measure_lib"],
    tags = ["manual"],
)

py_library(
    name = "setup_lib",
    srcs = ["setup.py"],
)

py_binary(
    name = "setup",
    srcs = [":setup_lib"],
    tags = ["manual"],
)
