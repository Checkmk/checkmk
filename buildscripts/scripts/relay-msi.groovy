#!groovy

/// file: relay-msi.groovy

void main() {
    def edition = params.EDITION ?: "cloud";
    def version = params.VERSION ?: "daily";

    def allowed_editions = ["cloud", "ultimate", "ultimatemt"];
    if (!(edition in allowed_editions)) {
        error("Edition '${edition}' is not supported for the relay MSI build. Allowed editions: ${allowed_editions}.");
    }

    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_vers_rc_aware = versioning.get_cmk_version(branch_name, branch_version, version);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_vers_rc_aware);

    // When FORCE_SIGN parameter is present we honour it. Otherwise we sign the MSI.
    def should_sign = (params.FORCE_SIGN == null) || (params.FORCE_SIGN == true);

    // Forward the pipeline version unchanged (like winagt-build does for the agent);
    // build-msi.ps1 normalises it into the strict x.x.x.x WiX requires.
    dir("${checkout_dir}") {
        if (should_sign) {
            // Serialise access to the shared YubiKey signing token via the
            // "win_sign_key" lock, the same way the agent build does (see
            // buildscripts/scripts/winagt-build.groovy).
            lock(label: "win_sign_key", quantity: 1, resource : null) {
                windows.build(
                    TARGET: 'relay_msi_with_sign',
                    VERSION: cmk_version,
                );
            }
        } else {
            windows.build(
                TARGET: 'relay_msi_no_sign',
                VERSION: cmk_version,
            );
        }
    }
}

return this;
