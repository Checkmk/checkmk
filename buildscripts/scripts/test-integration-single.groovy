#!groovy

/// file: test-integration-single.groovy

void main() {
    check_job_parameters([
        ["EDITION", true],  // the testees package long edition string (e.g. 'pro')
        ["DISTRO", true],  // the testees package distro string (e.g. 'ubuntu-24.04')
        ["FAKE_ARTIFACTS", true],  // forwarded to package build job
        "TEST_FILTER",  // a filter string to select which tests to run
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",  // the docker tag to use for building and testing, forwarded to packages build job
    ]);

    def single_tests = load("${checkout_dir}/buildscripts/scripts/utils/single_tests.groovy");
    def helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    def distro = params.DISTRO;
    def edition = params.EDITION;
    def fake_artifacts = params.FAKE_ARTIFACTS;
    def test_filter = params.TEST_FILTER;

    def make_target = "test-integration";
    def download_dir = "package_download";
    def test_results_dir = "test-results";

    if (test_filter.contains("-m medium_test_chain")) {
        // This test filtering is special in this job.
        // This job gets also triggered by the medium chain which is setting additional markers.
        // As only one marker can be set no "-m 'a' -m 'b'" is allowed
        // "TEST_FILTER" at single_test.groovy is single quoted, be carefull with the quotes used here for quoting
        test_filter = test_filter.replaceAll("-m medium_test_chain", '-m "medium_test_chain and not requires_non_root_user"');

        print(
            """
            Test filter changed as this job was triggered with '-m medium_test_chain'

            |===== CONFIGURATION ===============================
            |test_filter:.............. │${test_filter}│
            |===================================================
            """.stripMargin());
    } else {
        // Remember, the last "-m MARKER" is overruling all previous definitions
        // "TEST_FILTER" is prepended to the pytest call and thereby always the first source of settings
        make_target += "-k8s";
    }

    def setup_values = single_tests.common_prepare(
        version: "daily",
        make_target: make_target,
        docker_tag: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD
    );

    dir("${checkout_dir}") {
        stage("Fetch Checkmk package") {
            single_tests.fetch_package(
                // use the cross edition target or fall back to the value of edition
                edition: edition,
                distro: distro,
                download_dir: download_dir,
                bisect_comment: params.CIPARAM_BISECT_COMMENT,
                fake_artifacts: fake_artifacts,
                docker_tag: setup_values.docker_tag,
                safe_branch_name: setup_values.safe_branch_name,
            );
        }

        helper.execute_test([
            // k8s specific configs
            name: "${make_target}",
            container_name: "this-distro-container",
            callback: single_tests.&run_make_target_k8s,

            // test environment specific configs
            disable_hot_cache: true,
            prepare_fake_git_overlay: true,
            creds_usernames: [
                [credentialsId: "cmk-credentials", location: "/etc/.cmk-credentials"],
            ],

            // test specific configs
            result_path: "${checkout_dir}/test-results/${distro}",
            archive_pattern: "${test_results_dir}/**",
            edition: edition,
            docker_tag: setup_values.docker_tag,
            version: setup_values.cmk_version,
            distro: distro,
            branch_name: setup_values.safe_branch_name,
            make_target: "${make_target}",
            test_filter: test_filter,
            faked_artifacts: fake_artifacts,
            // ultimate can hit 120min during the nightly runs (without wait time)
            // runs of heavy chain are around 45-90min depending on the edition
            // using FoS of 3
            timeout: 360,
        ]);
    }

    stage("Process test reports") {
        // In k8s the generated JUnit files need to be created on workspace level to avoid
        // Cannot create directory '<JOB_NAME>/checkout/generatedJUnitFiles/<RANDOM_HASH>'
        // See also Change-Id: Id7495a6bf311d77adec239d44be243aebb07b2cf
        xunit([Custom(
            customXSL: "${checkout_dir}/buildscripts/scripts/schema/pytest-xunit.xsl",
            deleteOutputFiles: true,
            failIfNotNew: false,
            pattern: "checkout/test-results/**/junit.xml",
            skipNoTestFiles: false,
            stopProcessingIfError: true
        )]);
    }
}

return this;
