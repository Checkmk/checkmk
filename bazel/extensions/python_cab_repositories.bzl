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
    "core": "592af28b25b8142111b3600c82792f778ffb522b12768170a205fb90e40c72e8",
    "exe": "985e3ce8b3f0a432fdadfa5aacac506635816c5d24a36fd6222b9e390da279d5",
    "lib": "7d047ae8b57857e33c3827fe77b052297e61bdab6b3fd4fecd343c3c30e3a8ff",
    "pip": "c735e5c194e517ddf182a29d3b22fe61948cb09268aa6c064351a3ff69b30cb3",
    "ucrt": "a314817b93e1f66a79c4228a48d699523ce129d8ddfae6e7dd84e77fe88072c3",
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
