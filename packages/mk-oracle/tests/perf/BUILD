load("@aspect_rules_py//py:defs.bzl", "py_binary")

py_library(
    name = "bench-phases_lib",
    testonly = True,
    srcs = ["bench-phases.py"],
)

py_binary(
    name = "bench-phases",
    testonly = True,
    srcs = [":bench-phases_lib"],
    tags = ["manual"],
)

py_library(
    name = "measure_lib",
    testonly = True,
    srcs = ["measure.py"],
)

py_binary(
    name = "measure",
    testonly = True,
    srcs = [":measure_lib"],
    tags = ["manual"],
)

py_library(
    name = "setup_lib",
    testonly = True,
    srcs = ["setup.py"],
)

py_binary(
    name = "setup",
    testonly = True,
    srcs = [":setup_lib"],
    tags = ["manual"],
)
