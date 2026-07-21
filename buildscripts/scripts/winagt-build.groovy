#!groovy

/// file: winagt-build.groovy

void main() {
    check_job_parameters(["VERSION", "SIGN_METHOD"]);

    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_vers_rc_aware = versioning.get_cmk_version(branch_name, branch_version, params.VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_vers_rc_aware);

    // Choose the signing method. Azure signs in-process against the cloud service (no
    // YubiKey / win_sign_key lock); YubiKey is the fallback and keeps the hardware lock.
    def use_azure = (params.SIGN_METHOD == "azure");
    def sign_target = use_azure ? "agent_with_sign_azure" : "agent_with_sign";

    // Strip any quotes: on Windows agents `make print-%` echoes the value wrapped in
    // single quotes (defines.make), which cmd.exe does not strip, so branch_name may
    // arrive as e.g. '3.0.0'. Azure's CorrelationId is an opaque tracking string.
    def correlation_id = "${branch_name}_${env.AZURE_ARTIFACT_SIGNING_CORRELATION_ID_SUFFIX}".replaceAll("['\"]", "");

    def common_creds = [
        usernamePassword(
            credentialsId: 'nexus',
            passwordVariable: 'NEXUS_PASSWORD',
            usernameVariable: 'NEXUS_USERNAME'),
        string(
            credentialsId: "CI_TEST_SQL_DB_ENDPOINT",
            variable:"CI_TEST_SQL_DB_ENDPOINT"),
        string(
            credentialsId: "CI_ORA_TEST_PASSWORD",
            variable:"CI_ORA_TEST_PASSWORD"),
    ];

    dir("${checkout_dir}") {
        stage("make setversion") {
            bat("make -C agents\\wnx NEW_VERSION='${cmk_version}' setversion")
        }

        if (use_azure) {
            withCredentials(common_creds + [
                string(credentialsId: "azure_artifact_signing_client_secret", variable: "AZURE_ARTIFACT_SIGNING_CLIENT_SECRET"),
            ]) {
                // The windows.build function will create stages.
                withEnv([
                    "CMK_VERSION=${cmk_version}",
                    "AZURE_ARTIFACT_SIGNING_ENDPOINT=${env.AZURE_ARTIFACT_SIGNING_ENDPOINT}",
                    "AZURE_ARTIFACT_SIGNING_ACCOUNT=${env.AZURE_ARTIFACT_SIGNING_ACCOUNT}",
                    "AZURE_ARTIFACT_SIGNING_PROFILE=${env.AZURE_ARTIFACT_SIGNING_PROFILE}",
                    "AZURE_ARTIFACT_SIGNING_TENANT_ID=${env.AZURE_ARTIFACT_SIGNING_TENANT_ID}",
                    "AZURE_ARTIFACT_SIGNING_CLIENT_ID=${env.AZURE_ARTIFACT_SIGNING_CLIENT_ID}",
                    "AZURE_ARTIFACT_SIGNING_CORRELATION_ID=${correlation_id}",
                ]) {
                    windows.build(
                    TARGET: sign_target,
                    CREDS: NEXUS_USERNAME + ':' + NEXUS_PASSWORD,
                    CACHE_URL: 'https://artifacts.lan.tribe29.com/repository/omd-build-cache/'
                );
                }
            }
        } else {
            // Serialise access to the shared YubiKey signing token via the
            // "win_sign_key" lock.
            lock(label: "win_sign_key", quantity: 1, resource : null) {
                withCredentials(common_creds + [
                    string(
                        credentialsId: "sectigo_2023_pin",
                        variable: "SECTIGO_2023_PIN"
                    ),
                ]) {
                    // The windows.build function will create stages.
                    withEnv(["CMK_VERSION=${cmk_version}"]) {
                        windows.build(
                        TARGET: sign_target,
                        CREDS: NEXUS_USERNAME + ':' + NEXUS_PASSWORD,
                        CACHE_URL: 'https://artifacts.lan.tribe29.com/repository/omd-build-cache/'
                    );
                    }
                }
            }
        }

        // YubiKey requires a USB detach after signing; Azure does not.
        if (!use_azure) {
            stage("detach") {
                dir("agents\\wnx") {
                    bat("run.cmd --detach");
                }
            }
        }
    }
}

return this;
