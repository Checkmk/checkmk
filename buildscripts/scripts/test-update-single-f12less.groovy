#!groovy

/// file: test-update-single-f12less.groovy

def build_make_target(edition) {
    def prefix = "test-update-";
    def suffix = "-docker";
    switch(edition) {
        case 'enterprise':
            return prefix + "cee" + suffix;
        case 'cloud':
            return prefix + "cce" + suffix;
        default:
            error("The update tests are not yet enabled for edition: " + edition);
    }
}

def main() {
    check_job_parameters([
        ["EDITION", true],  // the testees package long edition string (e.g. 'enterprise')
        ["DISTRO", true],  // the testees package distro string (e.g. 'ubuntu-22.04')
        "VERSION",
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
        "EDITION",
    ]);

    def single_tests = load("${checkout_dir}/buildscripts/scripts/utils/single_tests.groovy");

    def version = params.VERSION;
    def distro = params.DISTRO;
    def edition = params.EDITION;

    def make_target = build_make_target(edition);
    def download_dir = "package_download";

    def setup_values = single_tests.common_prepare(version: params.VERSION, make_target: make_target);

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
                    single_tests.fetch_package(edition: edition, distro: distro, download_dir: download_dir);
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
