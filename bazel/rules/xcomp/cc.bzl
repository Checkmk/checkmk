"""Wrapper that lets users specify an alternative target platform."""

load(":private/xcomp/cc/cc_binary.bzl", _cc_binary = "cc_binary")
load(":private/xcomp/cc/cc_library.bzl", _cc_library = "cc_library")
load(":private/xcomp/cc/cc_shared_library.bzl", _cc_shared_library = "cc_shared_library")
load(":private/xcomp/cc/cc_test.bzl", _cc_test = "cc_test")

cc_binary = _cc_binary
cc_library = _cc_library
cc_shared_library = _cc_shared_library

_HERMETIC = Label("//bazel/platforms:x86_64-linux-gcc-hermetic")
_RUNTIME = "//omd/packages/cpp-libs:runtime"

def cc_test(name, data = [], env = {}, **kwargs):
    """cc_test that loads the shipped C++ runtime on the hermetic platform, like the site.

    Args:
        name: target name.
        data: runtime data.
        env: test environment.
        **kwargs: forwarded to the underlying rule.
    """
    platform = kwargs.get("platform")
    if platform and native.package_relative_label(platform) == _HERMETIC:
        data = data + [_RUNTIME]
        env = env | {"LD_LIBRARY_PATH": "$(rootpath %s)" % _RUNTIME}
    _cc_test(name = name, data = data, env = env, **kwargs)
