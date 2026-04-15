#!groovy

/// file: test-update-single-f12less-k8s.groovy

String build_make_target(edition, cross_edition_target="") {
    switch (edition) {
        // The make targets are written without the -docker suffix in tests/Makefile.
        case 'community':
            switch (cross_edition_target) {
                case 'ultimate':
                    return "test-update-cross-edition-community-to-ultimate";
                case 'pro':
                    return "test-update-cross-edition-community-to-pro";
                default:
                    return "test-update-community";
            }
        case 'pro':
            switch (cross_edition_target) {
                case 'ultimate':
                    return "test-update-cross-edition-pro-to-ultimate";
                case 'ultimatemt':
                    return "test-update-cross-edition-pro-to-ultimatemt";
                default:
                    return "test-update-pro";
            }
        case 'ultimate':
            return "test-update-ultimate";
        case 'cloud':
            return "test-update-cloud";
        case 'ultimatemt':
            return "test-update-ultimatemt";
        default:
            error("The update tests are not yet enabled for edition: " + edition);
    }
}

void main() {
    check_job_parameters([
        ["EDITION", true],  // the testees package long edition string (e.g. 'pro')
        ["DISTRO", true],  // the testees package distro string (e.g. 'ubuntu-24.04')
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",  // the docker tag to use for building and testing, forwarded to packages build job
        "FAKE_ARTIFACTS",
        "TEST_FILTER",  // a filter string to select which tests to run
        "VERSION",
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
        "EDITION",
        "CROSS_EDITION_TARGET",
        "OTEL_SDK_DISABLED",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
    ]);

    def single_tests = load("${checkout_dir}/buildscripts/scripts/utils/single_tests.groovy");
    def helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    def distro = params.DISTRO;
    def edition = params.EDITION;
    def fake_artifacts = params.FAKE_ARTIFACTS;

    def cross_edition_target = params.CROSS_EDITION_TARGET ?: "";
    if (cross_edition_target) {
        // see CMK-18366
        distro = "ubuntu-24.04";
    }
    def make_target = build_make_target(edition, cross_edition_target);
    def download_dir = "package_download";
    def test_results_dir = "test-results";

    def setup_values = single_tests.common_prepare(
        version: params.VERSION,
        make_target: make_target,
        docker_tag: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD
    );

    dir("${checkout_dir}") {
        stage("Fetch Checkmk package") {
            single_tests.fetch_package(
                // use the cross edition target or fall back to the value of edition
                edition: cross_edition_target ?: edition,
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
            credentialsUsernameId: "cmk-credentials",
            credentialsLocation: "/etc/.cmk-credentials",

            // test specific configs
            result_path: "${checkout_dir}/test-results/${distro}",
            archive_pattern: "${test_results_dir}/**",
            edition: cross_edition_target ?: edition,
            docker_tag: setup_values.docker_tag,
            version: setup_values.cmk_version,
            distro: distro,
            branch_name: setup_values.safe_branch_name,
            make_target: "-C tests ${make_target}", // k8s does not allow dir()
            test_filter: params.TEST_FILTER,
            faked_artifacts: fake_artifacts,
            // ultimate can hit 40min during the nightly runs (without wait time)
            // runs of heavy chain are around 10-30min depending on the edition
            // using FoS of 3
            timeout: 120,
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
