#!groovy

/// file: winagt-test-build.groovy

def main() {
    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version = versioning.get_cmk_version(branch_name, branch_version, "daily");

    dir("${checkout_dir}") {
        stage("make setversion") {
            bat("make -C agents\\wnx NEW_VERSION='${cmk_version}' setversion");
        }
        withCredentials([
            string(
                credentialsId: "CI_TEST_SQL_DB_ENDPOINT",
                variable:"CI_TEST_SQL_DB_ENDPOINT"),
            string(
                credentialsId: "CI_ORA2_DB_TEST",
                variable:"CI_ORA2_DB_TEST"),
        ]) {
            windows.build(
                TARGET: 'agent_no_sign'
            );
        }
    }
}

return this;
