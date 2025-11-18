load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")

FAMILIES = [
    d.removeprefix("cmk/plugins/")
    for d in glob(
        ["cmk/plugins/*"],
        exclude_directories = 0,
    )
]

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [":%s" % f for f in FAMILIES],
    tags = ["no-mypy"],
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

filegroup(
    name = "py_typed",
    srcs = [
        "cmk/plugins/%s/py.typed" % f
        for f in FAMILIES
    ],
)

[filegroup(
    name = "checkman-%s" % family,
    srcs = glob(
        ["cmk/plugins/%s/checkman/**/*" % family],
        allow_empty = True,
    ),
) for family in FAMILIES]

[pkg_files(
    name = "libexec-%s" % family,
    srcs = glob(
        ["cmk/plugins/%s/libexec/*" % family],
        allow_empty = True,
    ),
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/python%s/site-packages/cmk/plugins/%s/libexec" % (PYTHON_MAJOR_DOT_MINOR, family),
) for family in FAMILIES]

py_wheel(
    name = "wheel",
    distribution = "cmk-plugins",
    strip_path_prefixes = ["packages/cmk-plugins"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [
        ":%s" % f
        for f in FAMILIES
    ] + [":checkman-%s" % f for f in FAMILIES],
)

package_wheel(
    name = "pkg_tar",
    additional_files = [":libexec-%s" % f for f in FAMILIES],
    visibility = ["//visibility:public"],
    whl = "wheel",
)

# One wheel per family:
# Very similar to the above, but with the loop outside.
[py_wheel(
    name = "wheel-%s" % family,
    distribution = "cmk-plugins-%s" % family,
    strip_path_prefixes = ["packages/cmk-plugins"],
    version = "1.0.0",
    deps = [
        ":%s" % family,
        ":checkman-%s" % family,
    ],
) for family in FAMILIES]

[package_wheel(
    name = "pkg_tar-%s" % family,
    additional_files = [":libexec-%s" % family],
    visibility = ["//visibility:public"],
    whl = "wheel-%s" % family,
) for family in FAMILIES]
