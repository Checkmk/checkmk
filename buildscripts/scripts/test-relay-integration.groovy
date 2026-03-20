#!groovy

/// file: test-relay-integration.groovy

void main() {
    check_job_parameters([
        ["EDITION", true],  // the testees package long edition string (e.g. 'ultimate')
        ["DISTRO", true],  // the testees package distro string (e.g. 'ubuntu-24.04')
        "TEST_FILTER",  // a filter string to select which tests to run
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",  // the docker tag to use for building and testing, forwarded to packages build job
        "VERSION",
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
        "EDITION",
    ]);

    def single_tests = load("${checkout_dir}/buildscripts/scripts/utils/single_tests.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, params.VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def version = params.VERSION;
    def distro = params.DISTRO;
    def edition = params.EDITION;

    def make_target = "test-relay-integration";
    def download_dir = "downloaded_packages_for_docker_tests/${cmk_version_rc_aware}";
    def package_distro = "ubuntu-22.04";

    def setup_values = single_tests.common_prepare(
        version: version,
        make_target: make_target,
        docker_tag: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD
    );

    currentBuild.description += (
        """
        |Run relay integration tests<br>
        |safe_branch_name: ${safe_branch_name}<br>
        |branch_version: ${branch_version}<br>
        |cmk_version: ${cmk_version}<br>
        |cmk_version_rc_aware: ${cmk_version_rc_aware}<br>
        |edition: ${edition}<br>
        |make_target: ${make_target}<br>
        """.stripMargin());

    print(
        """
        |===== CONFIGURATION ===============================
        |safe_branch_name:...... │${safe_branch_name}│
        |branch_version:........ │${branch_version}│
        |cmk_version:........... │${cmk_version}
        |cmk_version_rc_aware:.. │${cmk_version_rc_aware}
        |edition:............... │${edition}│
        |checkout_dir:.......... │${checkout_dir}│
        |make_target:........... │${make_target}│
        |docker_tag:............ │${setup_values.docker_tag}│
        |===================================================
        """.stripMargin());

    // this is a quick fix for FIPS based tests, see CMK-20851
    def build_node = params.CIPARAM_OVERRIDE_BUILD_NODE;
    if (build_node == "fips") {
        // Do not start builds on FIPS node
        println("Detected build node 'fips', switching this to 'fra'.");
        build_node = "fra";
    }

    dir("${checkout_dir}") {
        stage("Prepare workspace") {
            sh("rm -rf ${download_dir} && mkdir -p ${download_dir}");
        }

        stage("Fetch Checkmk package") {
            single_tests.fetch_package(
                edition: edition,
                distro: package_distro,
                download_dir: download_dir,
                bisect_comment: params.CIPARAM_BISECT_COMMENT,
                fake_artifacts: params.FAKE_WINDOWS_ARTIFACTS,
                docker_tag: setup_values.docker_tag,
                safe_branch_name: setup_values.safe_branch_name,
            );
        }

        // Tag the relay image with the commit SHA so concurrent jobs on the same agent
        // cannot collide on a shared :<version> tag, and so the test can never silently
        // pull a stale image from nexus pushed by an earlier commit on the same day.
        def short_sha = cmd_output("git rev-parse --short=8 HEAD");
        def relay_image_tag = "check-mk-relay:${setup_values.cmk_version}-${short_sha}";

        inside_container(
            args: [
                "--env HOME=/home/jenkins",
                "--env RELAY_IMAGE_TAG=${relay_image_tag}",
            ],
            set_docker_group_id: true,
            ulimit_nofile: 1024,
            mount_credentials: true,
            privileged: true,
        ) {
            stage("Build relay image") {
                sh("""
                    bazel run \
                        --cmk_edition=${edition} \
                        --cmk_version=${setup_values.cmk_version} \
                    //omd/non-free/relay:image_docker
                    docker tag check-mk-relay:latest ${relay_image_tag}
                """);
            }

            stage("Relay end-to-end integration test") {
                try {
                    docker.withRegistry(DOCKER_REGISTRY, "nexus") {
                        dir("${checkout_dir}") {
                            sh("""
                                WORKSPACE='${checkout_dir}' \
                                BRANCH='${setup_values.safe_branch_name}' \
                                EDITION='${edition}' \
                                VERSION='${cmk_version_rc_aware}' \
                                DISTRO='${distro}' \
                                TEST_FILTER='${params.TEST_FILTER}' \
                                make -C tests ${make_target}
                            """);
                        }
                    }
                } finally {
                    sh("docker rmi -f ${relay_image_tag} || true");
                }
            }
        }
    }
}

return this;
