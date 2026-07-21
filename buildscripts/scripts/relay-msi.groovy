#!groovy

/// file: relay-msi.groovy

void main() {
    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    def branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_vers_rc_aware = versioning.get_cmk_version(branch_name, branch_version, params.VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_vers_rc_aware);

    def edition = params.EDITION;

    // Strip any quotes: on Windows agents `make print-%` echoes the value wrapped in
    // single quotes (defines.make), which cmd.exe does not strip, so branch_name may
    // arrive as e.g. '3.0.0'. Azure's CorrelationId is an opaque tracking string.
    def correlation_id = "${branch_name}_${env.AZURE_ARTIFACT_SIGNING_CORRELATION_ID_SUFFIX}".replaceAll("['\"]", "");

    // When FORCE_SIGN parameter is present we honour it. Otherwise we sign the MSI.
    def should_sign = (params.FORCE_SIGN == null) || (params.FORCE_SIGN == true);

    // Choose the signing method, mirroring winagt-build.groovy. Azure signs in-process
    // against the cloud service (no YubiKey / win_sign_key lock); YubiKey is the fallback.
    def use_azure = (params.SIGN_METHOD == "azure");
    def sign_target = use_azure ? 'relay_msi_with_sign_azure' : 'relay_msi_with_sign';

    def azure_creds = [
        string(credentialsId: "azure_artifact_signing_client_secret", variable: "AZURE_ARTIFACT_SIGNING_CLIENT_SECRET"),
    ];

    def allowed_editions = ["cloud", "ultimate", "ultimatemt"];
    if (!(edition in allowed_editions)) {
        error("Edition '${edition}' is not supported for the relay MSI build. Allowed editions: ${allowed_editions}.");
    }

    // Forward the pipeline version unchanged (like winagt-build does for the agent);
    // build-msi.ps1 normalises it into the strict x.x.x.x WiX requires.
    dir("${checkout_dir}") {
        if (use_azure && should_sign) {
            withCredentials(azure_creds) {
                withEnv([
                    "AZURE_ARTIFACT_SIGNING_ENDPOINT=${env.AZURE_ARTIFACT_SIGNING_ENDPOINT}",
                    "AZURE_ARTIFACT_SIGNING_ACCOUNT=${env.AZURE_ARTIFACT_SIGNING_ACCOUNT}",
                    "AZURE_ARTIFACT_SIGNING_PROFILE=${env.AZURE_ARTIFACT_SIGNING_PROFILE}",
                    "AZURE_ARTIFACT_SIGNING_TENANT_ID=${env.AZURE_ARTIFACT_SIGNING_TENANT_ID}",
                    "AZURE_ARTIFACT_SIGNING_CLIENT_ID=${env.AZURE_ARTIFACT_SIGNING_CLIENT_ID}",
                    "AZURE_ARTIFACT_SIGNING_CORRELATION_ID=${correlation_id}",
                ]) {
                    windows.build(
                        TARGET: sign_target,
                        VERSION: cmk_version,
                    );
                }
            }
        } else if (should_sign) {
            withCredentials([string(credentialsId: "sectigo_2023_pin", variable: "SECTIGO_2023_PIN")]) {
                // Serialise access to the shared YubiKey signing token via the
                // "win_sign_key" lock, the same way the agent build does (see
                // buildscripts/scripts/winagt-build.groovy).
                lock(label: "win_sign_key", quantity: 1, resource : null) {
                    windows.build(
                        TARGET: sign_target,
                        VERSION: cmk_version,
                    );
                }
            }
        } else {
            windows.build(
                TARGET: 'relay_msi_no_sign',
                VERSION: cmk_version,
            );
        }

        // Unit tests: validate the MSI we just built (structure + signature).
        // test-msi.ps1 gates via exit code AND emits a JUnit XML.
        try {
            windows.build(
                TARGET: 'relay_msi_test',
                REQUIRE_SIGNATURE: should_sign,
            );
        } finally {
            // Publish the JUnit XML
            archiveArtifacts(
                allowEmptyArchive: true,
                artifacts: "artefacts/relay_msi_test_results.xml",
                fingerprint: true,
            );
            test_jenkins_helper.analyse_issues("JUNIT", "artefacts/relay_msi_test_results.xml");
        }
    }
}

return this;
