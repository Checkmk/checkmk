"""select()s deciding whether the agent .rpm is signed.

Shared by agents/BUILD, omd/BUILD and bazel/rules/sign_package_tests, so the
tests resolve exactly what the real consumers resolve.
"""

def signed_or_unsigned_agent_rpm(signed, unsigned):
    """Selects between the signed and the unsigned agent .rpm.

    The unsigned one is used if signing is disabled, artifacts are faked, or
    no signing key is configured, see
    //:agent_package_signing_effectively_disabled.

    Args:
        signed: the value to use for the signed .rpm.
        unsigned: the value to use for the unsigned .rpm.

    Returns:
        A select() between both values.
    """
    return select({
        Label("//:agent_package_signing_effectively_disabled"): unsigned,
        "//conditions:default": signed,
    })

def requires_signed_agent_rpm():
    """target_compatible_with for targets that must not ship an unsigned .rpm.

    They are incompatible if the unsigned agent .rpm is used, unless signing
    is disabled or artifacts are faked, see //:agent_package_signing_missing.

    Returns:
        A select() for target_compatible_with.
    """
    return select({
        Label("//:agent_package_signing_missing"): [Label("@platforms//:incompatible")],
        "//conditions:default": [],
    })
