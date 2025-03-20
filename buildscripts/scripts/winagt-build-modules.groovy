#!groovy

/// file: winagt-build-modules.groovy

/// builds python module for windows agent

def main() {
    check_job_parameters(["VERSION"]);

    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware)

    dir("${checkout_dir}") {
        bat("make -C agents\\wnx NEW_VERSION='${cmk_version}' setversion")

        stage("Run cached build") {
            withCredentials([usernamePassword(
                    credentialsId: 'nexus',
                    passwordVariable: 'NEXUS_PASSWORD',
                    usernameVariable: 'NEXUS_USERNAME')]) {
                windows.build(
                    TARGET: 'cached',
                    CREDS: NEXUS_USERNAME+':'+NEXUS_PASSWORD,
                    CACHE_URL: 'https://artifacts.lan.tribe29.com/repository/omd-build-cache/'
                )
            }
        }
    }
}

return this;
