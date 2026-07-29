"""Asserts the toolchain's Bazel-only arguments stay out of cargo build scripts.

rules_rust builds $CFLAGS / $CXXFLAGS / $LDFLAGS for cargo build scripts from the
cc toolchain with no action variables set. Anything in the toolchain that is meant
only for Bazel's own cc_* actions therefore has to be gated on an action variable
(requires_not_none), or it leaks into every build script that compiles C or C++.
"""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts")
load("//bazel/toolchains/cc/clang/xwin/args:crt.bzl", "RELEASE_CRT_LINK_ARGS")

_TRIPLE = "x86_64-pc-windows-msvc"

_SYSROOT = "xwin_sysroot"

_SYSROOT_PREFIXES = [
    "${pwd}/external/",
    "external/",
]

def _isystem(path):
    return ["-Xclang", "-internal-isystem", "-Xclang", "<SYSROOT>/" + path]

# What the toolchain is meant to hand a cargo build script, in order.
_EXPECTED = {
    "CFLAGS": ["--target=" + _TRIPLE] +
              _isystem("crt/include") +
              _isystem("sdk/include/ucrt") +
              _isystem("sdk/include/um") +
              _isystem("sdk/include/shared") +
              ["-DNDEBUG", "/MT", "/O2"],
    "CXXFLAGS": ["--target=" + _TRIPLE, "/EHsc"] +
                _isystem("crt/include") +
                _isystem("sdk/include/ucrt") +
                _isystem("sdk/include/um") +
                _isystem("sdk/include/shared") +
                ["-DNDEBUG", "/MT", "/O2"],
    # The CRT half comes from the same list the toolchain links against, so
    # changing that list does not need a change here; an extra flag still fails.
    "LDFLAGS": [
        "/MACHINE:X64",
        "/LIBPATH:<SYSROOT>/crt/lib/x86_64",
        "/LIBPATH:<SYSROOT>/sdk/lib/ucrt/x86_64",
        "/LIBPATH:<SYSROOT>/sdk/lib/um/x86_64",
    ] + RELEASE_CRT_LINK_ARGS,
}

def _normalize(flag):
    """Collapses @xwin_sysroot's path, keeping any flag prefix.

    The canonical repository name carries a +_repo_rules<N>+ component whose index
    shifts whenever a repo rule is added earlier in MODULE.bazel, so matching it
    literally would break on unrelated edits.

    Args:
        flag: one argument off the build script's command line.

    Returns:
        The argument with the sysroot path replaced by <SYSROOT>.
    """
    for prefix in _SYSROOT_PREFIXES:
        start = flag.find(prefix)
        if start == -1:
            continue
        marker = flag.find(_SYSROOT, start)
        if marker == -1:
            continue
        return flag[:start] + "<SYSROOT>" + flag[marker + len(_SYSROOT):]
    return flag

def _build_script_action(env):
    for action in analysistest.target_actions(env):
        if action.env and "CFLAGS" in action.env:
            return action
    return None

def _check(env, var, raw):
    actual = [_normalize(flag) for flag in raw.split(" ") if flag]
    expected = _EXPECTED[var]
    if actual == expected:
        return

    unexpected = [flag for flag in actual if flag not in expected]
    missing = [flag for flag in expected if flag not in actual]
    detail = []
    if unexpected:
        detail.append(
            ("unexpected {}: gate it on an action variable, or add it to " +
             "_EXPECTED if a build script really should get it").format(unexpected),
        )
    if missing:
        detail.append(
            "missing {}: a gate is too aggressive".format(missing),
        )
    if not detail:
        detail.append("same arguments, different order")

    asserts.equals(
        env,
        expected,
        actual,
        "${} does not match the build-script contract -- {}".format(
            var,
            "; ".join(detail),
        ),
    )

def _impl(ctx):
    env = analysistest.begin(ctx)
    action = _build_script_action(env)

    asserts.false(
        env,
        action == None,
        "no build-script action carrying $CFLAGS was found; the test is not " +
        "looking at what it thinks it is",
    )
    if action == None:
        return analysistest.end(env)

    for var in _EXPECTED:
        _check(env, var, action.env.get(var, ""))

    return analysistest.end(env)

def _make(compilation_mode):
    return analysistest.make(
        impl = _impl,
        config_settings = {
            "//command_line_option:compilation_mode": compilation_mode,
            "//command_line_option:platforms": ["@@//bazel/platforms:x86_64-windows-msvc"],
        },
    )

# One per -c mode: the build-script command lines are release regardless, so all
# three assert the same thing. A mode argument that lost its gate fails two of
# the three.
build_script_flags_fastbuild_test = _make("fastbuild")
build_script_flags_dbg_test = _make("dbg")
build_script_flags_opt_test = _make("opt")
