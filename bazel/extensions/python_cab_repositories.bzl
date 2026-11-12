"""Module extension declaring the repositories of the Windows agent build."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive", "http_file")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")
load("//:package_versions.bzl", "PYTHON_VERSION_WINDOWS")
load("//agents/modules/windows:python_msis.bzl", "PYTHON_MSI_FEATURES")

# sha256 of each per-feature python.org MSI, for PYTHON_VERSION_WINDOWS.  The URLs
# derive from that version below, so this map is the only part a version bump has to
# touch; regenerate it with //agents/modules/windows:refresh_msi_pins.  Its keys are
# PYTHON_MSI_FEATURES, each naming the @python_msi_<key> repo declared below.
_MSI_SHA256 = {
    "core": "1ab04330cedbf1e12e9a11a3afb21679e808d02bffe49dff5483dfaa7641b1ef",
    "exe": "3d8b229039e276aadc880e52c4aea3ab3b9af4934e34d6be08c9cf78919c9e55",
    "lib": "cf9dd1af2ad9d3f8c9f0ce76c56c6def378f6ab1b79f964dd54e0ea958403c08",
    "pip": "42741e3241aeff190674d635c2b65984262e9059788040d04c6c7e66ae0ca42b",
    "ucrt": "7abe902a0458d01b8fbcfb10ebb634398a85e3acb0ad6ec5ed6db6785af76e12",
}

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

    if sorted(_MSI_SHA256) != sorted(PYTHON_MSI_FEATURES):
        fail("_MSI_SHA256 must pin exactly the PYTHON_MSI_FEATURES %r, got %r" % (
            PYTHON_MSI_FEATURES,
            sorted(_MSI_SHA256),
        ))
    for feature in PYTHON_MSI_FEATURES:
        http_file(
            name = "python_msi_" + feature,
            downloaded_file_path = feature + ".msi",
            sha256 = _MSI_SHA256[feature],
            urls = [
                "https://www.python.org/ftp/python/{version}/amd64/{feature}.msi".format(
                    feature = feature,
                    version = PYTHON_VERSION_WINDOWS,
                ),
                # The per-feature MSIs are all called <feature>.msi upstream, and the
                # mirror is flat, so the copy there carries the version in its name.
                UPSTREAM_MIRROR_URL + "python-{version}-amd64-{feature}.msi".format(
                    feature = feature,
                    version = PYTHON_VERSION_WINDOWS,
                ),
            ],
        )

repos = module_extension(
    implementation = _repos_impl,
)
