"""Module extension declaring the Windows test VM image and its media."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")
load("//agents/wnx/test-vm:image.bzl", "WINDOWS_TEST_IMAGE")

def _repos_impl(mctx):
    # The Windows test VM image the *-qemu tiers resume (agents/wnx/test-vm):
    # a cleanly shut down, zstd-compressed qcow2.
    http_file(
        name = "win2022_core_image",
        downloaded_file_path = "win2022-core.qcow2",
        sha256 = WINDOWS_TEST_IMAGE.sha256,
        urls = [UPSTREAM_MIRROR_URL + WINDOWS_TEST_IMAGE.file],
    )

    # The media the image is built from (agents/wnx/test-vm, bazel run
    # only): Microsoft's Eval media and SQL Server 2022 Developer, mirrored
    # on Nexus under versioned names.
    http_file(
        name = "win2022_eval_iso",
        downloaded_file_path = "win2022-eval.iso",
        # SERVER_EVAL_x64FRE_en-us.iso, build 20348.587 (fwlink 2195280).
        sha256 = "3e4fa6d8507b554856fc9ca6079cc402df11a8b79344871669f0251535255325",
        urls = [UPSTREAM_MIRROR_URL + "SERVER_EVAL_x64FRE_en-us-20348.587.iso"],
    )

    # The guest agent (qemu-ga) and the virtio-serial driver it talks
    # through, from the virtio-win "stable-virtio" release
    # (fedorapeople.org/groups/virt/virtio-win/direct-downloads).
    http_file(
        name = "virtio_win_iso",
        downloaded_file_path = "virtio-win.iso",
        sha256 = "303f7ae40dad495d6ae474fdc571df58958a4dbc5c37a522d80f9a203867949d",
        urls = [UPSTREAM_MIRROR_URL + "virtio-win-0.1.302.iso"],
    )
    http_file(
        name = "mssql2022_dev_iso",
        downloaded_file_path = "SQLServer2022-x64-ENU-Dev.iso",
        sha256 = "80d2cd75dd2b28098c0182f50ad86bd44f9b3a9f357c30ff617480a1497daffd",
        urls = [UPSTREAM_MIRROR_URL + "SQLServer2022-x64-ENU-Dev-16.0.1000.6.iso"],
    )
    http_file(
        name = "mssql2022_cu",
        # Bump MSSQL_VERSION in make_image.py with it.
        downloaded_file_path = "SQLServer2022-KB5104824-x64.exe",
        sha256 = "675e3cedd6c7a3d0ffbe713e46e54a86a92af7b96ca4a6beb987ae99c79b96f5",
        urls = [UPSTREAM_MIRROR_URL + "SQLServer2022-KB5104824-x64.exe"],
    )
    http_file(
        name = "msodbcsql17_msi",
        downloaded_file_path = "msodbcsql17.msi",
        sha256 = "0f6428706ac1fa4863d10e515135b587de88011813131c0a43f70cd70dc0bd4e",
        urls = [UPSTREAM_MIRROR_URL + "msodbcsql17-17.11.1.1-x64.msi"],
    )

    # Fully pinned by sha256: nothing for MODULE.bazel.lock to record, so
    # re-pinning the image (at least every 180 days) does not touch it.
    return mctx.extension_metadata(reproducible = True)

test_vm = module_extension(
    implementation = _repos_impl,
)
