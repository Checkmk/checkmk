#!groovy

/// file: test-python3-unit-all.groovy

void main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def safe_branch_name = versioning.safe_branch_name();

    // The branch-specific part must not contain dots (e.g. 2.5.0),
    // because this results in an invalid branch name.
    // The pod templates uses - instead.
    def container_safe_branch_name = safe_branch_name.replace(".", "-");

    dir("${checkout_dir}") {
        withCredentials([string(credentialsId: "CI_TEST_SQL_DB_ENDPOINT", variable: "CI_TEST_SQL_DB_ENDPOINT")]) {
            test_jenkins_helper.execute_test([
                name: "test-unit-all",
                cmd: """\
make_rc=0
BAZEL_EXTRA_TAG_FILTERS="-cpp" buildscripts/scripts/bazel_test_ci.sh \
    --test_verbose_timeout_warnings \
    --test_env=TZ='America/Chicago' \
    --cmk_edition=ultimate \
    -- //... || make_rc=\$?
buildscripts/scripts/bazel_test_post_archive_xunit.sh || :
exit \$make_rc""",
                container_name: "ubuntu-2404-${container_safe_branch_name}-latest",
                disable_hot_cache: true,
            ]);
        }

        archiveArtifacts(
            allowEmptyArchive: true,
            artifacts: "results/unit/**/test.xml",
            fingerprint: true,
        );
        test_jenkins_helper.analyse_issues("JUNIT", "results/unit/**/test.xml");
    }
}

return this;
