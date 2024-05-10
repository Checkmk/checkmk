#!groovy

/// file: winagt-build-modules.groovy

/// builds python module for windows agent

// TODO: pipelineTriggers([pollSCM('H/15 * * * *')]),

def main() {
    check_job_parameters(["VERSION"]);

    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version_rc_aware = versioning.get_cmk_version(branch_name, branch_version, VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    dir("${checkout_dir}") {
        setCustomBuildProperty(
            key: "path_hashes",
            value: scm_directory_hashes(scm.extensions)
        );

        stage("make setversion") {
            bat("make -C agents\\wnx NEW_VERSION='${cmk_version}' setversion");
        }

        stage("Run cached build") {
            withCredentials([usernamePassword(
                    credentialsId: 'nexus',
                    passwordVariable: 'NEXUS_PASSWORD',
                    usernameVariable: 'NEXUS_USERNAME')]) {
                windows.build(
                    TARGET: 'cached',
                    CREDS: NEXUS_USERNAME+':'+NEXUS_PASSWORD,
                    CACHE_URL: 'https://artifacts.lan.tribe29.com/repository/omd-build-cache/'
                );
            }
        }
    }
}

return this;
