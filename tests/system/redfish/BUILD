load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

exports_files(["dev-requirements.in"])

py_library(
    name = "redfish",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    deps = [
        requirement("pytest"),
        requirement("grequests"),
        requirement("multipart"),
        requirement("opentelemetry-instrumentation-requests"),
        "//tests/testlib",
    ],
)
