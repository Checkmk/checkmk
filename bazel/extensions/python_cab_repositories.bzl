"""Module extension declaring the repositories of the Windows agent build."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive", "http_file")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

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

    http_file(
        name = "python_msi_ucrt",
        downloaded_file_path = "ucrt.msi",
        sha256 = "c35e76105318b7472c6028e8d4a2f9b8ec1a3ef02897b4e49350c8adb84a2105",
        url = "https://www.python.org/ftp/python/3.14.7/amd64/ucrt.msi",
    )
    http_file(
        name = "python_msi_core",
        downloaded_file_path = "core.msi",
        sha256 = "3dfcfe7b42e6f2d683be427af62369761c7e6627aff6a8da2f439a9d11e62cdf",
        url = "https://www.python.org/ftp/python/3.14.7/amd64/core.msi",
    )
    http_file(
        name = "python_msi_exe",
        downloaded_file_path = "exe.msi",
        sha256 = "63035cb1fc01ec085c0f18e73f8c1b000ca148378f4f4b1db11f3baabcc8cf3a",
        url = "https://www.python.org/ftp/python/3.14.7/amd64/exe.msi",
    )
    http_file(
        name = "python_msi_lib",
        downloaded_file_path = "lib.msi",
        sha256 = "d68a92dcc61addb49e4678f60af2838d7675991341c9bf0facd2c5e7283841c3",
        url = "https://www.python.org/ftp/python/3.14.7/amd64/lib.msi",
    )
    http_file(
        name = "python_msi_pip",
        downloaded_file_path = "pip.msi",
        sha256 = "b9c87eee34ab2ded2702b1fb26ea031b07ffbb665617336b2a70508e660153eb",
        url = "https://www.python.org/ftp/python/3.14.7/amd64/pip.msi",
    )

repos = module_extension(
    implementation = _repos_impl,
)
