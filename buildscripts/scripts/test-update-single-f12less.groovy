#!groovy

/// file: test-update-single-f12less.groovy

String build_make_target(edition, cross_edition_target="") {
    switch (edition) {
        // The make targets are written without the -docker suffix in tests/Makefile.
        case 'community':
            switch (cross_edition_target) {
                case 'ultimate':
                    return "test-update-cross-edition-community-to-ultimate-docker";
                case 'pro':
                    return "test-update-cross-edition-community-to-pro-docker";
                default:
                    return "test-update-community-docker";
            }
        case 'pro':
            switch (cross_edition_target) {
                case 'ultimate':
                    return "test-update-cross-edition-pro-to-ultimate-docker";
                case 'ultimatemt':
                    return "test-update-cross-edition-pro-to-ultimatemt-docker";
                default:
                    return "test-update-pro-docker";
            }
        case 'ultimate':
            return "test-update-ultimate-docker";
        case 'cloud':
            return "test-update-cloud-docker";
        case 'ultimatemt':
            return "test-update-ultimatemt-docker";
        default:
            error("The update tests are not yet enabled for edition: " + edition);
    }
}

void main() {
    check_job_parameters([
        ["EDITION", true],  // the testees package long edition string (e.g. 'pro')
        ["DISTRO", true],  // the testees package distro string (e.g. 'ubuntu-24.04')
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",  // the docker tag to use for building and testing, forwarded to packages build job
        "FAKE_WINDOWS_ARTIFACTS",
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

    def distro = params.DISTRO;
    def edition = params.EDITION;
    def fake_windows_artifacts = params.FAKE_WINDOWS_ARTIFACTS;

    def cross_edition_target = params.CROSS_EDITION_TARGET ?: "";
    if (cross_edition_target) {
        // see CMK-18366
        distro = "ubuntu-24.04";
    }
    def make_target = build_make_target(edition, cross_edition_target);
    def download_dir = "package_download";

    def setup_values = single_tests.common_prepare(
        version: params.VERSION,
        make_target: make_target,
        docker_tag: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD
    );

    // todo: add upstream project to description
    // todo: add error to description
    // todo: build progress mins?

    dir("${checkout_dir}") {
        stage("Fetch Checkmk package") {
            single_tests.fetch_package(
                // use the cross edition target or fall back to the value of edition
                edition: cross_edition_target ?: edition,
                distro: distro,
                download_dir: download_dir,
                bisect_comment: params.CIPARAM_BISECT_COMMENT,
                fake_windows_artifacts: fake_windows_artifacts,
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
                            result_path: "${checkout_dir}/test-results/${distro}",
                            // use the cross edition target or fall back to the value of edition
                            edition: cross_edition_target ?: edition,
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
                    single_tests.archive_and_process_reports(test_results: "test-results/**");
                }
            }
        }
    }
}

return this;
