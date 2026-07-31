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
        sha256 = "b173e03056eff8798729c602df992c1cc6b724f56465e39bbe1d01afeae1f369",
        url = "https://www.python.org/ftp/python/3.13.15/amd64/ucrt.msi",
    )
    http_file(
        name = "python_msi_core",
        downloaded_file_path = "core.msi",
        sha256 = "eff25b160b54a77c5953cf5803fc147a1ced084513265dfefc227583b1355484",
        url = "https://www.python.org/ftp/python/3.13.15/amd64/core.msi",
    )
    http_file(
        name = "python_msi_exe",
        downloaded_file_path = "exe.msi",
        sha256 = "47f02452bde1f05b4d06fb93841ce380624c882ef75caddd1b1207d1a36bb4d2",
        url = "https://www.python.org/ftp/python/3.13.15/amd64/exe.msi",
    )
    http_file(
        name = "python_msi_lib",
        downloaded_file_path = "lib.msi",
        sha256 = "6d3130114d7f57eaa33d86e8366a669dfc73cfe8df772bef93ce2d9ea799f751",
        url = "https://www.python.org/ftp/python/3.13.15/amd64/lib.msi",
    )
    http_file(
        name = "python_msi_pip",
        downloaded_file_path = "pip.msi",
        sha256 = "1bc9cfa07a92da66335cc7252dfb3d7ca318facd3966fd15574014466cccf37e",
        url = "https://www.python.org/ftp/python/3.13.15/amd64/pip.msi",
    )

repos = module_extension(
    implementation = _repos_impl,
)
