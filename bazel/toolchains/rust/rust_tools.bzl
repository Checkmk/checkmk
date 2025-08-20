def _rustc_impl(ctx):
    tc = ctx.toolchains["@rules_rust//rust:toolchain_type"]

    # Expose the toolchain's rustc as this target's only file.
    files = [tc.rustc]

    # Also bring along any inputs rustc needs (sysroot, etc.) so they’re on the action graph.
    run = ctx.runfiles(files = files + list(getattr(tc, "rustc_inputs", [])))
    return DefaultInfo(files = depset(files), runfiles = run)

def _cargo_impl(ctx):
    tc = ctx.toolchains["@rules_rust//rust:toolchain_type"]
    cargo = getattr(tc, "cargo", None)
    if cargo == None:
        fail("Selected Rust toolchain does not provide cargo.")
    return DefaultInfo(files = depset([cargo]), runfiles = ctx.runfiles(files = [cargo]))

rustc = rule(
    implementation = _rustc_impl,
    toolchains = ["@rules_rust//rust:toolchain_type"],
)

cargo = rule(
    implementation = _cargo_impl,
    toolchains = ["@rules_rust//rust:toolchain_type"],
)
