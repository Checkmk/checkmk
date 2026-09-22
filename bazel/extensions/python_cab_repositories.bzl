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
    "core": "eff25b160b54a77c5953cf5803fc147a1ced084513265dfefc227583b1355484",
    "exe": "47f02452bde1f05b4d06fb93841ce380624c882ef75caddd1b1207d1a36bb4d2",
    "lib": "6d3130114d7f57eaa33d86e8366a669dfc73cfe8df772bef93ce2d9ea799f751",
    "pip": "1bc9cfa07a92da66335cc7252dfb3d7ca318facd3966fd15574014466cccf37e",
    "ucrt": "b173e03056eff8798729c602df992c1cc6b724f56465e39bbe1d01afeae1f369",
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
