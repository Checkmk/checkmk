"""Platform transition for cross-compilation support."""

def _transition_platform_impl(settings, attr):
    return {
        "//command_line_option:compilation_mode": getattr(attr, "compilation_mode", "") or settings["//command_line_option:compilation_mode"],
        "//command_line_option:platforms": str(attr.platform),
    }

transition_platform = transition(
    implementation = _transition_platform_impl,
    inputs = ["//command_line_option:compilation_mode"],
    outputs = [
        "//command_line_option:platforms",
        "//command_line_option:compilation_mode",
    ],
)
