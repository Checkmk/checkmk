"""A container image that runs one Python module as a service.

The image has four parts:

* the distroless base image: glibc and the CA certificates, no shell
* the interpreter of the Bazel toolchain, which also runs the tests
* the libraries of the service, from the repo lock
* the package of the service

The image starts the interpreter directly. It needs no shell and no writable
directory, and it runs as a user that is not root.
"""

load("@aspect_rules_py//py/unstable:defs.bzl", "py_venv")
load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load", "oci_push")
load("@tar.bzl", "mtree_mutate", "mtree_spec", "tar")
load("//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")

# The base is for this platform only.
_PLATFORM = [
    "@platforms//cpu:x86_64",
    "@platforms//os:linux",
]

def _layer(name, srcs, strip_prefix, package_dir):
    """Packs the files of `srcs` below `strip_prefix` into `package_dir`."""
    mtree_spec(
        name = name + "_files",
        srcs = srcs,
    )
    mtree_mutate(
        name = name + "_mtree",
        mtree = name + "_files",
        package_dir = package_dir,
        strip_prefix = strip_prefix,
    )
    tar(
        name = name,
        srcs = srcs,
        compress = "gzip",
        mtree = name + "_mtree",
    )

def py_service_image(
        name,
        library,
        module,
        data = [],
        env = {},
        exposed_ports = [],
        repo_tags = [],
        repository = None,
        visibility = None):
    """Declares the image `name` and the target `name_load`, which loads it into Docker.

    With `repository`, it also declares the target `name_push`.

    Args:
        name: Name of the image target.
        library: The py_library of the service. Its import root must be its Bazel package.
        module: The module that the image runs, as in `python -m`.
        data: Files of the package that the service reads at run time.
        env: Environment variables of the image.
        exposed_ports: Ports of the service, for example ["8080/tcp"].
        repo_tags: Tags that `name_load` gives the image.
        repository: The registry path that `name_push` pushes the image to.
        visibility: Visibility of the image.
    """
    package = native.package_name()

    # One directory with all libraries. Two libraries with the same file are an error.
    venv = name + "_venv"
    py_venv(
        name = venv,
        package_collisions = "error",
        deps = [library],
    )
    _layer(
        name = name + "_libraries",
        srcs = [venv],
        package_dir = "app/site-packages",
        # The path has the Python version of the Bazel toolchain. The constant is the
        # version of the Checkmk Python. The repo lock keeps both on one minor version.
        strip_prefix = "{}/.{}/lib/python{}/site-packages".format(package, venv, PYTHON_MAJOR_DOT_MINOR),
    )
    _layer(
        name = name + "_package",
        srcs = [library] + data,
        package_dir = "app/src",
        strip_prefix = package,
    )

    # No stamp and no creation time: the same content gives the same digest.
    oci_image(
        name = name,
        base = "@distroless_cc_debian13_linux_amd64",
        entrypoint = [
            "/app/python/bin/python3",
            # Keep the working directory and the home of the user off the import path.
            "-P",
            "-s",
            "-m",
            module,
        ],
        env = {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": "/app/site-packages:/app/src",
            # The OpenSSL of the interpreter does not look there on its own.
            "SSL_CERT_FILE": "/etc/ssl/certs/ca-certificates.crt",
        } | env,
        exposed_ports = exposed_ports,
        target_compatible_with = _PLATFORM,
        tars = [
            "//bazel/rules/py_service_image:python_layer",
            name + "_libraries",
            name + "_package",
        ],
        # the user "nonroot" of the base
        user = "65532:65532",
        visibility = visibility,
    )
    oci_load(
        name = name + "_load",
        image = name,
        repo_tags = repo_tags,
    )
    if repository:
        # The tag is the start of the digest. A push of the same content then changes
        # nothing in the registry, so each run of a pipeline can push.
        native.genrule(
            name = name + "_tag",
            srcs = [name + ".digest"],
            outs = [name + ".tag"],
            # The digest is "sha256:" and 64 characters.
            cmd = "cut -c 8-19 $< > $@",
            target_compatible_with = _PLATFORM,
        )
        oci_push(
            name = name + "_push",
            image = name,
            remote_tags = name + "_tag",
            repository = repository,
            target_compatible_with = _PLATFORM,
        )
