"""Module extension declaring the media of the Windows test VM image."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def _repos_impl(mctx):
    # The media the image is built from (agents/wnx/test-vm, bazel run
    # only): Microsoft's Eval media, mirrored on Nexus under a versioned
    # name.
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

    # Fully pinned by sha256: nothing for MODULE.bazel.lock to record.
    return mctx.extension_metadata(reproducible = True)

test_vm = module_extension(
    implementation = _repos_impl,
)
