load("//bazel/rules:local_archive.bzl", "local_archive")

def asio_workspace():
    # Newer versions available from https://registry.bazel.build/modules/asio
    version_str = "1.34.2-patched"
    filename = "asio-" + version_str
    local_archive(
        name = "asio",
        src = "//:third_party/asio/" + filename + ".tar.gz",
        sha256 = "09b9fe5c670c7bd47c7ee957cd9c184b4c8f0620d5b08b38ce837a24df971bca",
        strip_prefix = filename,
        build_file = "@omd_packages//omd/packages/asio:BUILD.asio.bazel",
    )
