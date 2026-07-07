#!groovy

/// file: test-integration-otel.groovy

void main() {
    check_job_parameters([
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",  // the docker tag to use for building and testing, forwarded to packages build job
        ["DISTRO", true],  // the testees package distro string (e.g. 'ubuntu-24.04')
        ["EDITION", true],  // the testees package long edition string (e.g. 'pro')
        "FAKE_ARTIFACTS",
        "TEST_FILTER",  // a filter string to select which tests to run
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
    ]);

    def single_tests = load("${checkout_dir}/buildscripts/scripts/utils/single_tests.groovy");

    def disable_cache = params.DISABLE_CACHE;
    def distro = params.DISTRO;
    def edition = params.EDITION;
    def fake_artifacts = params.FAKE_ARTIFACTS;
    def force_build = params.DISABLE_JENKINS_CACHE == true;

    def download_dir = "package_download";
    def make_target = "test-integration-otel-docker";
    def result_dir = "test-results";

    def setup_values = single_tests.common_prepare(
        version: "daily",
        make_target: make_target,
        docker_tag: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD
    );

    // todo: add upstream project to description
    // todo: add error to description
    // todo: build progress mins?

    dir("${checkout_dir}") {
        stage("Prepare workspace") {
            sh("""
                rm -rf ${result_dir} ${download_dir}
                mkdir -p ${result_dir} ${download_dir}
            """);
        }

        stage("Fetch Checkmk package") {
            single_tests.fetch_package(
                edition: edition,
                distro: distro,
                download_dir: download_dir,
                bisect_comment: params.CIPARAM_BISECT_COMMENT,
                fake_artifacts: fake_artifacts,
                disable_cache: disable_cache,
                force_build: force_build,
                docker_tag: setup_values.docker_tag,
                safe_branch_name: setup_values.safe_branch_name,
            );
        }

        inside_container(
            args: [
                "--env HOME=/home/jenkins",
            ],
            set_docker_group_id: true,
            ulimit_nofile: 1024,
            mount_credentials: true,
            privileged: true,
        ) {
            try {
                stage("Run `make ${make_target}`") {
                    dir("${checkout_dir}/tests") {
                        single_tests.run_make_target(
                            result_path: "${checkout_dir}/${result_dir}/${distro}",
                            edition: edition,
                            docker_tag: setup_values.docker_tag,
                            version: setup_values.cmk_version,
                            distro: distro,
                            branch_name: setup_values.safe_branch_name,
                            make_target: make_target,
                            test_filter: params.TEST_FILTER,
                            faked_artifacts: fake_artifacts,
                        );
                    }
                }
            } finally {
                stage("Archive / process test reports") {
                    single_tests.archive_and_process_reports(test_results: "${result_dir}/**");
                }
            }
        }
    }
}

return this;
