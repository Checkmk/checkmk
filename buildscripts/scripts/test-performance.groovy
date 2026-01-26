#!groovy

/// file: test-performance.groovy

void main() {
    check_job_parameters([
        "EDITION",
        "DISTRO",
        "FAKE_WINDOWS_ARTIFACTS",
    ]);

    def single_tests = load("${checkout_dir}/buildscripts/scripts/utils/single_tests.groovy");
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def result_dir = "${checkout_dir}/results";
    def distro = params.DISTRO;
    def edition = params.EDITION;
    def fake_windows_artifacts = params.FAKE_WINDOWS_ARTIFACTS;

    // Use the directory also used by tests/testlib/containers.py to have it find
    // the downloaded package.
    def download_dir = "package_download";
    def make_target = "test-performance-docker";

    def setup_values = single_tests.common_prepare(
        version: "daily",
        make_target: make_target,
        docker_tag: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD
    );

    dir("${checkout_dir}") {
        stage("Prepare workspace") {
            sh("""
                rm -rf "${result_dir}"
                mkdir -p "${result_dir}"
            """);
        }

        stage("Fetch Checkmk package") {
            single_tests.fetch_package(
                edition: edition,
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
            withCredentials([
                string(
                    credentialsId: 'JIRA_API_TOKEN_QA_ALERTS',
                    variable: 'QA_JIRA_API_TOKEN'
                ),
            ]) {
                withCredentialFileAtLocation(
                    credentialsId: "QA_POSTGRES_KEY_FILE",
                    location: "${checkout_dir}/QA_POSTGRES_KEY",
                ) {
                    withCredentialFileAtLocation(
                        credentialsId: "QA_POSTGRES_CERT_FILE",
                        location: "${checkout_dir}/QA_POSTGRES_CERT",
                    ) {
                        withCredentialFileAtLocation(
                            credentialsId: "QA_ROOT_CERT_FILE",
                            location: "${checkout_dir}/QA_ROOT_CERT",
                        ) {
                            test_jenkins_helper.execute_test([
                                name: make_target,
                                cmd: "make -C tests ${make_target}",
                                // output_file: "test-performance.txt",
                                container_name: "this-distro-container",
                            ]);
                        }
                    }
                }
            }
        }
    }

    stage("Archive / process test reports") {
        dir("${result_dir}") {
            show_duration("archiveArtifacts") {
                archiveArtifacts("**");
            }
            xunit([Custom(
                customXSL: "${checkout_dir}/buildscripts/scripts/schema/pytest-xunit.xsl",
                deleteOutputFiles: true,
                failIfNotNew: true,
                pattern: "**/junit.xml",
                skipNoTestFiles: false,
                stopProcessingIfError: true
            )]);
        }
    }
}

return this;
