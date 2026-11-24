"""Module extension declaring the repositories of the Windows agent build."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")
load("//:package_versions.bzl", "PYTHON_VERSION_WINDOWS")

# The python-build-standalone release whose x86_64-pc-windows-msvc install_only
# archive of PYTHON_VERSION_WINDOWS the cabs are built from, and that archive's
# sha256 (in the release's SHA256SUMS).  The URLs derive from both below, so a
# version bump touches these two lines and PYTHON_VERSION_WINDOWS.
_PBS_RELEASE = "20261110"
_PBS_SHA256 = "a0e4e14d152efbd2a66e4873efe0b4ab42e1ee759441dbc23af034236d7a09cd"

def _repos_impl(_mctx):
    http_archive(
        name = "cabarchive",
        build_file = "//agents/modules/windows:cabarchive.BUILD.bazel",
        integrity = "sha256-tQixytiQhX5V8/eiAnynvtudwF3l7/B/gon5VGIAp6o=",
        strip_prefix = "cabarchive-0.2.5",
        urls = [
            "https://files.pythonhosted.org/packages/source/c/cabarchive/cabarchive-0.2.5.tar.gz",
            UPSTREAM_MIRROR_URL + "cabarchive-0.2.5.tar.gz",
        ],
    )

    # The sources of //agents/modules/windows:pyyaml_wheel, whose version must match.
    # TODO: Drop it once PyYAML publishes win_amd64 wheels for PYTHON_VERSION_WINDOWS.
    http_archive(
        name = "pyyaml_sdist",
        build_file = "//agents/modules/windows:pyyaml.BUILD.bazel",
        sha256 = "d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f",
        strip_prefix = "pyyaml-6.0.3",
        urls = [
            "https://files.pythonhosted.org/packages/source/p/pyyaml/pyyaml-6.0.3.tar.gz",
            UPSTREAM_MIRROR_URL + "pyyaml-6.0.3.tar.gz",
        ],
    )

    # Unpacked by Bazel; its BUILD file leaves out what the cabs never ship.
    archive = "cpython-{version}+{release}-x86_64-pc-windows-msvc-install_only.tar.gz".format(
        release = _PBS_RELEASE,
        version = PYTHON_VERSION_WINDOWS,
    )
    http_archive(
        name = "python_windows_standalone",
        build_file = "//agents/modules/windows:python_windows_standalone.BUILD.bazel",
        sha256 = _PBS_SHA256,
        strip_prefix = "python",
        urls = [
            "https://github.com/astral-sh/python-build-standalone/releases/download/{release}/{archive}".format(
                archive = archive,
                release = _PBS_RELEASE,
            ),
            UPSTREAM_MIRROR_URL + archive,
        ],
    )

repos = module_extension(
    implementation = _repos_impl,
)
