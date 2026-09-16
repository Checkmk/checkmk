"""Verifies sign_package's action never declares the signing key as an input."""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts")

def _sign_action(env):
    for action in analysistest.target_actions(env):
        if action.mnemonic == "SignPackage":
            return action
    return None

def _impl(ctx):
    env = analysistest.begin(ctx)
    action = _sign_action(env)

    asserts.false(env, action == None, "no SignPackage action found")
    if action == None:
        return analysistest.end(env)

    # Every input must be either the unsigned package (src) or the checked-in
    # signer tool - never anything path-shaped like a signing key, which
    # would mean the secret leaked into the action graph as a declared input.
    input_paths = [f.path for f in action.inputs.to_list()]
    asserts.equals(
        env,
        2,
        len(input_paths),
        "sign_package's action should declare exactly two inputs (the " +
        "unsigned package and the signer script), found: %s" % input_paths,
    )
    for path in input_paths:
        asserts.true(
            env,
            path.endswith("fake.rpm") or path.endswith("sign_package.sh"),
            "unexpected input on sign_package's action: %s" % path,
        )

    # Only PATH may ever reach the action's environment - never the full
    # --action_env-populated default shell env. The key and passphrase
    # paths reach the action as plain arguments, not through the
    # environment at all.
    allowed_env_keys = ["PATH"]
    for key in action.env.keys():
        asserts.true(
            env,
            key in allowed_env_keys,
            "sign_package's action leaked an unexpected env var: %s " % key +
            "(only %s are allowed)" % allowed_env_keys,
        )

    return analysistest.end(env)

sign_package_only_declares_src_as_input_test = analysistest.make(
    _impl,
    config_settings = {
        str(Label("//bazel/rules:signing_key_file")): "/dummy/analysis-test.key",
    },
)
