"""Module extension declaring the repositories of the Windows agent build."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive", "http_file")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")
load("//:package_versions.bzl", "PYTHON_VERSION_WINDOWS")

# sha256 of each per-feature python.org MSI, for PYTHON_VERSION_WINDOWS.  The URLs
# derive from that version below, so this map is the only part a version bump has to
# touch; regenerate it with //agents/modules/windows:refresh_msi_pins.  Each key names
# the @python_msi_<key> repo declared below, which is the default of python_cab's
# msi_<key> attribute in //agents/modules/windows:python_cab.bzl -- keep the two sets
# of names in sync.
_MSI_SHA256 = {
    "core": "3dfcfe7b42e6f2d683be427af62369761c7e6627aff6a8da2f439a9d11e62cdf",
    "exe": "63035cb1fc01ec085c0f18e73f8c1b000ca148378f4f4b1db11f3baabcc8cf3a",
    "lib": "d68a92dcc61addb49e4678f60af2838d7675991341c9bf0facd2c5e7283841c3",
    "pip": "b9c87eee34ab2ded2702b1fb26ea031b07ffbb665617336b2a70508e660153eb",
    "ucrt": "c35e76105318b7472c6028e8d4a2f9b8ec1a3ef02897b4e49350c8adb84a2105",
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

    for feature, sha256 in _MSI_SHA256.items():
        http_file(
            name = "python_msi_" + feature,
            downloaded_file_path = feature + ".msi",
            sha256 = sha256,
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
