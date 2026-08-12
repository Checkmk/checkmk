#!groovy

/// file: test-system-singlesite-single.groovy

void main() {
    check_job_parameters([
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",  // the docker tag to use for building and testing, forwarded to packages build job
        ["DISTRO", true],  // the testees package distro string (e.g. 'ubuntu-24.04')
        ["EDITION", true],  // the testees package long edition string (e.g. 'pro')
        ["FAKE_ARTIFACTS", true],  // forwarded to package build job
        "TEST_FILTER",  // a filter string to select which tests to run
    ]);

    def single_tests = load("${checkout_dir}/buildscripts/scripts/utils/single_tests.groovy");
    def helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    def disable_cache = params.DISABLE_CACHE;
    def disable_signing = params.DISABLE_CMK_DISTRO_PACKAGE_SIGNING;
    def distro = params.DISTRO;
    def edition = params.EDITION;
    def fake_artifacts = params.FAKE_ARTIFACTS;
    def force_build = params.DISABLE_JENKINS_CACHE == true;
    def test_filter = params.TEST_FILTER;

    def download_dir = "package_download";
    def make_target = "test-system-singlesite";
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
                bisect_comment: params.CIPARAM_BISECT_COMMENT,
                disable_cache: disable_cache,
                disable_signing: disable_signing,
                distro: distro,
                docker_tag: setup_values.docker_tag,
                download_dir: download_dir,
                edition: edition,
                fake_artifacts: fake_artifacts,
                force_build: force_build,
                safe_branch_name: setup_values.safe_branch_name,
            );
        }

        /// Set only when the medium chain triggered this run as a shard. Everything
        /// sharding needs hangs off this one value, because the script is shared with
        /// heavy/ and the other editions, which must keep running exactly as before.
        ///
        /// Deliberately not in check_job_parameters above: those jobs have no such
        /// parameter and requiring it would fail them. Absent reads as null, the
        /// elvis turns that into "", which means "not sharded".
        ///
        /// tests/conftest.py reads it as the default of --shard-durations-build.
        def shard_build_based_on = params.SHARD_BUILD_BASED_ON ?: "";

        withEnv([
            "SHARD_BUILD_BASED_ON=${shard_build_based_on}",
            /// What cmk_dev's extract_credentials() needs on top of the two
            /// credentials below, there is no hardcoded fallback.
            "JENKINS_URL=${env.JENKINS_URL}",
        ]) {
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
                /// Only a sharded run talks to the Jenkins API, to read the runtimes
                /// of the build named in SHARD_BUILD_BASED_ON. An empty list makes
                /// withCredentialEnv() skip withCredentials() altogether, so every
                /// other job on this script keeps the environment it had before and
                /// never sees these credentials.
                creds_env: shard_build_based_on ? [
                    usernamePassword(
                        credentialsId: "jenkins-api-token",
                        usernameVariable: "JENKINS_USERNAME",
                        passwordVariable: "JENKINS_PASSWORD",
                    ),
                ] : [],

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
                force_build: force_build,
                disable_cache: disable_cache,
                // ultimate can hit 120min during the nightly runs (without wait time)
                // runs of heavy chain are around 45-90min depending on the edition
                // using FoS of 3
                timeout: 360,
            ]);
        }
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
