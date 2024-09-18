load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@omd_packages//omd/packages/rules:package_wheel.bzl", "package_wheel")

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
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-crypto",
    strip_path_prefixes = ["packages/cmk-crypto"],
    # TODO: Duplicated from pyproject.toml
    version = "0.9.0",
    deps = [
        ":cmk-crypto",
    ],
)

package_wheel(wheel_target = "wheel")
