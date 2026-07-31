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

    def use_azure = (params.SIGN_METHOD == "azure");
    def sign_target = use_azure ? "agent_with_sign_azure" : "agent_with_sign";

    dir("${checkout_dir}") {
        stage("make setversion") {
            bat("make -C agents\\wnx NEW_VERSION='${cmk_version}' setversion")
        }

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

        // The correlation ID suffix is a shared secret appended to every CorrelationId we send to
        // Azure, so signing requests which did not originate from our CI can be spotted in the
        // signing diagnostics. It therefore lives in the credential store, not in an env var. It
        // stays bound for the whole build: the Azure client echoes the CorrelationId, and Jenkins
        // only masks the secret inside this block.
        def sign_creds = use_azure ? [
            string(credentialsId: "azure_artifact_signing_client_secret",   variable: "AZURE_ARTIFACT_SIGNING_CLIENT_SECRET"),
            string(credentialsId: "azure_artifact_signing_correlation_suffix", variable: "AZURE_ARTIFACT_SIGNING_CORRELATION_SUFFIX"),
        ] : [
            string(credentialsId: "sectigo_2023_pin",   variable: "SECTIGO_2023_PIN")
        ];

        withCredentials(common_creds + sign_creds) {
            // Assembled inside the binding block: the suffix is only available there.
            def correlation_id = use_azure ? windows.azure_signing_correlation_id(branch_name) : "";

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
