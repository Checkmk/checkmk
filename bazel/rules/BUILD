load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

exports_files([
    # The shared runner behind rust_wine_test() (xcomp/rust_wine_test.bzl).
    "xcomp/rust-test-wine.sh",
    # Sourced by the scripts of package_msi.bzl rules.
    "xcomp/package_msi.sh",
])

py_binary(
    name = "set_runpath_tree",
    srcs = ["set_runpath_tree.py"],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "deb_installed_size",
    srcs = ["deb_installed_size.py"],
    visibility = ["//visibility:public"],
)

py_pytest_main(
    name = "__test__",
    deps = [requirement("pytest")],
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/*.py"]) + [":__test__.py"],
    imports = ["."],
    main = "__test__.py",
    deps = [
        ":__test__",
        ":deb_installed_size",
        requirement("pytest"),
    ],
)

# Lets shellcheck see these scripts. Nothing depends on this target.
sh_library(
    name = "shell_scripts",
    srcs = ["xcomp/package_msi.sh"],
)
