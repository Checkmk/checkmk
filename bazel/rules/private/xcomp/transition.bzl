def _transition_platform_impl(_, attr):
    return {"//command_line_option:platforms": str(attr.platform)}

transition_platform = transition(
    implementation = _transition_platform_impl,
    inputs = [],
    outputs = ["//command_line_option:platforms"],
)
