#!groovy

/// file: test-composition-single-f12less.groovy

def main() {
    check_job_parameters([
        "EDITION",
        "DISTRO",
        "USE_CASE",
        "FAKE_WINDOWS_ARTIFACTS"
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
    ]);

    def single_tests = load("${checkout_dir}/buildscripts/scripts/utils/single_tests.groovy");
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    def distro = params.DISTRO;
    def edition = params.EDITION;
    def fake_windows_artifacts = params.FAKE_WINDOWS_ARTIFACTS;

    // TODO: we should always use USE_CASE directly from the job parameters
    def use_case = (params.USE_CASE == "fips") ? params.USE_CASE : "daily_tests"
    test_jenkins_helper.assert_fips_testing(use_case, NODE_LABELS);

    // Use the directory also used by tests/testlib/containers.py to have it find
    // the downloaded package.
    def download_dir = "package_download";
    def make_target = "test-composition-docker";

    def setup_values = single_tests.common_prepare(version: "daily", make_target: make_target);

    // todo: add upstream project to description
    // todo: add error to description
    // todo: build progress mins?

    stage("Prepare workspace") {
        inside_container(
            args: [
                "--env HOME=/home/jenkins",
            ],
            set_docker_group_id: true,
            ulimit_nofile: 1024,
            mount_credentials: true,
            priviliged: true,
        ) {
            single_tests.prepare_workspace(
                cleanup: [
                    "${WORKSPACE}/test-results",
                    "${checkout_dir}/${download_dir}"
                ],
                make_venv: true
            );

            dir("${checkout_dir}") {
                stage("Fetch Checkmk package") {
                    single_tests.fetch_package(
                        edition: edition,
                        distro: distro,
                        download_dir: download_dir,
                        bisect_comment: params.CIPARAM_BISECT_COMMENT,
                        fake_windows_artifacts: fake_windows_artifacts
                    );
                }
                try {
                    stage("Run `make ${make_target}`") {
                        dir("${checkout_dir}/tests") {
                            single_tests.run_make_target(
                                result_path: "${WORKSPACE}/test-results/${distro}",
                                edition: edition,
                                docker_tag: setup_values.docker_tag,
                                version: "daily",
                                distro: distro,
                                branch_name: setup_values.safe_branch_name,
                                make_target: make_target,
                            );
                        }
                    }
                } finally {
                    stage("Archive / process test reports") {
                        dir("${WORKSPACE}") {
                            single_tests.archive_and_process_reports(test_results: "test-results/**");
                        }
                    }
                }
            }
        }
    }
}

return this;
