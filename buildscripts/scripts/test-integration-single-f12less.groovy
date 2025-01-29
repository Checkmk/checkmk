#!groovy

/// file: test-integration-single-f12less.groovy

def main() {
    check_job_parameters([
        ["EDITION", true],  // the testees package long edition string (e.g. 'enterprise')
        ["DISTRO", true],  // the testees package distro string (e.g. 'ubuntu-22.04')
        // "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD", // test base image tag (todo)
        // "DISABLE_CACHE",    // forwarded to package build job (todo)
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
    ]);

    def single_tests = load("${checkout_dir}/buildscripts/scripts/utils/single_tests.groovy");

    def distro = params.DISTRO;
    def edition = params.EDITION;

    def make_target = "test-integration-docker";
    def download_dir = "package_download";

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
                make_venv: true,
            );

            dir("${checkout_dir}") {
                stage("Fetch Checkmk package") {
                    single_tests.fetch_package(
                        edition: edition,
                        distro: distro,
                        download_dir: download_dir,
                        bisect_comment: params.CIPARAM_BISECT_COMMENT
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
