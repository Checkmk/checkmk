#!groovy

/// file: winagt-test-integration.groovy

void main() {
    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version = versioning.get_cmk_version(branch_name, branch_version, "daily").replaceAll("['\"]", "");

    stage("Run 'test_integration'") {
        dir("${checkout_dir}") {
            withEnv(["CMK_VERSION=${cmk_version}"]) {
                withNexusCredentials {
                    windows.build(
                        TARGET: 'test_integration',
                        CREDS: NEXUS_USERNAME + ':' + NEXUS_PASSWORD,
                        CACHE_URL: 'https://artifacts.lan.tribe29.com/repository/omd-build-cache/'
                    );
                }
            }
        }
    }
}

return this;
