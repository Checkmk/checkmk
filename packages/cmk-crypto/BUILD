load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-crypto",
    srcs = [
        "cmk/crypto/__init__.py",
        "cmk/crypto/certificate.py",
        "cmk/crypto/deprecated.py",
        "cmk/crypto/hash.py",
        "cmk/crypto/keys.py",
        "cmk/crypto/password.py",
        "cmk/crypto/password_hashing.py",
        "cmk/crypto/pem.py",
        "cmk/crypto/secrets.py",
        "cmk/crypto/symmetric.py",
        "cmk/crypto/totp.py",
        "cmk/crypto/x509.py",
    ],
    data = [":py_typed"],
    imports = ["."],
    visibility = [
        "//cmk:__pkg__",
        "//non-free/packages:__subpackages__",
        "//packages:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:site",
        requirement("bcrypt"),
        requirement("cryptography"),
        requirement("python-dateutil"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["cmk-crypto"],
    tags = ["no-mypy"],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]) + [":__test__.py"],
    main = "__test__.py",
    deps = [
        ":__test__",
        ":cmk-crypto",
        requirement("cryptography"),
        requirement("pytest"),
        requirement("time-machine"),
        requirement("python-dateutil"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-crypto",
    strip_path_prefixes = ["packages/cmk-crypto"],
    # TODO: Duplicated from pyproject.toml
    version = "1.1.0",
    deps = [
        ":cmk-crypto",
        ":py_typed",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

filegroup(
    name = "py_typed",
    srcs = ["cmk/crypto/py.typed"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
