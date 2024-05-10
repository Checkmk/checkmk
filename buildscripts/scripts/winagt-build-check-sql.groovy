#!groovy

/// file: winagt-build-check-sql.groovy

def main() {
    check_job_parameters(["VERSION"]);

    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version = versioning.get_cmk_version(branch_name, branch_version, VERSION);

    dir("${checkout_dir}") {
        stage("make setversion") {
            bat("make -C agents\\wnx NEW_VERSION='${cmk_version}' setversion");
        }

        withCredentials([string(
            credentialsId: "CI_TEST_SQL_DB_ENDPOINT",
            variable:"CI_TEST_SQL_DB_ENDPOINT"
        )]) {
            windows.build(
                TARGET: 'mk_sql_no_sign',
            );
        }
    }
}

return this;
