#!groovy

/// file: winagt-build.groovy

def main() {
    check_job_parameters(["VERSION"]);

    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_vers_rc_aware = versioning.get_cmk_version(branch_name, branch_version, VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_vers_rc_aware);

    dir("${checkout_dir}") {
        setCustomBuildProperty(
            key: "path_hashes",
            value: scm_directory_hashes(scm.extensions)
        );

        stage("make setversion") {
            bat("make -C agents\\wnx NEW_VERSION='${cmk_version}' setversion")
        }

        withCredentials([
            usernamePassword(
                credentialsId: 'win_sign',
                passwordVariable: 'WIN_SIGN_PASSWORD',
                usernameVariable: ''),
            string(
                credentialsId: "CI_TEST_SQL_DB_ENDPOINT",
                variable:"CI_TEST_SQL_DB_ENDPOINT"),
        ]) {
            windows.build(
                TARGET: 'agent_with_sign',
                PASSWORD: WIN_SIGN_PASSWORD,
            );
        }

        stage("detach") {
            dir("agents\\wnx"){
                bat("run.cmd --detach");
            }
        }

    }
}

return this;
