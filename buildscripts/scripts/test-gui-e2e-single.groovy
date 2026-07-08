#!groovy

/// file: test-gui-e2e-single.groovy

void main() {
    check_job_parameters([
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",  // the docker tag to use for building and testing, forwarded to packages build job
        ["DISTRO", true],  // the testees package distro string (e.g. 'ubuntu-24.04')
        ["EDITION", true],  // the testees package long edition string (e.g. 'pro')
        "FAKE_ARTIFACTS",
        "TEST_FILTER",  // a filter string to select which tests to run
        "USE_CASE",
        "VERSION",
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
    def use_case = (params.USE_CASE == "fips") ? params.USE_CASE : "daily_tests";

    helper.assert_fips_testing(use_case, NODE_LABELS);

    def download_dir = "package_download";
    def make_target = "test-gui-e2e-${edition}";
    def test_results_dir = "test-results";

    def setup_values = single_tests.common_prepare(
        version: params.VERSION,
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

        // this task needs to be done before the make test target
        // this command is called by pytest during the test for "test_filesystem_email_notifications"
        // but the postfix is never configured properly. Calling this before the test, it does everything
        // properly
        def do_before = "sudo --preserve-env=POD_LABEL,KUBERNETES_PORT tests/scripts/setup_postfix.sh root";
        helper.execute_test([
            // k8s specific configs
            name: "${make_target}",
            container_name: "this-distro-container",
            // "cmd" is executed before "callback"
            cmd: do_before,
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
            make_target: "-C tests ${make_target}", // k8s does not allow dir()
            test_filter: test_filter,
            faked_artifacts: fake_artifacts,
            disable_cache: disable_cache,
            // can hit 150min during the heavy chain runs (without wait time)
            // runs of heavy chain are around 15-30min depending on the edition
            // Only Pro edition usually takes 150min
            // using FoS of 3
            timeout: edition.toLowerCase() == "pro" ? 450 : 90,
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
