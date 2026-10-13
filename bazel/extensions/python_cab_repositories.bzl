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
    "core": "507599467fafc5e8783961bd76db6e5a206d58bc968f06728c8a3865fc7337af",
    "exe": "fa39afc12c0778464273167046d7755c93902ecbc2293682724fdb7023f07cca",
    "lib": "ee15c9b1cd71465a60f7a37cf0528e0446398ff94020c0075514c43ab0655d3f",
    "pip": "90b1bdae0804309e2b1f71df1652a7551121c6f1095a0c99b4f6eb8d739ab070",
    "ucrt": "c0dc366e60851d85ea7341672b3041b5faf808149280476f961c7054828421e7",
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
