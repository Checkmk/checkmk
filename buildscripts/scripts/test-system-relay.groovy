#!groovy

/// file: test-system-relay.groovy

/// The cheap artifact checks run first: a binary missing from the image fails in
/// seconds, instead of after a whole site and relay stack has been brought up.
/// RELAY_IMAGE_TAG is already in the environment. The cleanup covers both stages,
/// so a failure in either one still removes the image from the agent.
void run_relay_tests(Map args) {
    try {
        stage("Relay image artifact test") {
            dir("${args.checkout_dir}") {
                sh("make -C tests test-artifact-relay-image");
            }
        }

        stage("Relay end-to-end integration test") {
            docker.withRegistry(args.docker_registry, "nexus") {
                dir("${args.checkout_dir}") {
                    sh("""
                        WORKSPACE='${args.checkout_dir}' \
                        BRANCH='${args.branch}' \
                        EDITION='${args.edition}' \
                        VERSION='${args.version}' \
                        DISTRO='${args.distro}' \
                        TEST_FILTER='${args.test_filter}' \
                        make -C tests ${args.make_target}
                    """);
                }
            }
        }
    } finally {
        sh("docker rmi -f ${args.relay_image_tag} || true");
    }
}

void main() {
    check_job_parameters([
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",  // the docker tag to use for building and testing, forwarded to packages build job
        ["DISTRO", true],  // the testees package distro string (e.g. 'ubuntu-24.04')
        ["EDITION", true],  // the testees package long edition string (e.g. 'ultimate')
        "TEST_FILTER",  // a filter string to select which tests to run
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

    def build_node = params.CIPARAM_OVERRIDE_BUILD_NODE;
    def disable_cache = params.DISABLE_CACHE;
    def disable_signing = params.DISABLE_CMK_DISTRO_PACKAGE_SIGNING;
    def distro = params.DISTRO;
    def edition = params.EDITION;
    def fake_artifacts = params.FAKE_ARTIFACTS;
    def force_build = params.DISABLE_JENKINS_CACHE == true;
    def version = params.VERSION;

    def download_dir = "downloaded_packages_for_docker_tests/${cmk_version_rc_aware}";
    def package_distro = "ubuntu-22.04";
    def make_target = "test-system-relay";

    def setup_values = single_tests.common_prepare(
        version: version,
        make_target: make_target,
        docker_tag: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD
    );

    currentBuild.description += (
        """
        |Run relay integration tests<br>
        |branch_version: ${branch_version}<br>
        |cmk_version: ${cmk_version}<br>
        |cmk_version_rc_aware: ${cmk_version_rc_aware}<br>
        |edition: ${edition}<br>
        |make_target: ${make_target}<br>
        |safe_branch_name: ${safe_branch_name}<br>
        """.stripMargin());

    print(
        """
        |===== CONFIGURATION ===============================
        |branch_version:........ │${branch_version}│
        |checkout_dir:.......... │${checkout_dir}│
        |cmk_version:........... │${cmk_version}
        |cmk_version_rc_aware:.. │${cmk_version_rc_aware}
        |disable_cache:......... │${disable_cache}│
        |disable_signing:....... │${disable_signing}│
        |docker_tag:............ │${setup_values.docker_tag}│
        |edition:............... │${edition}│
        |fake_artifacts:........ │${fake_artifacts}│
        |force_build:........... │${force_build}│
        |make_target:........... │${make_target}│
        |safe_branch_name:...... │${safe_branch_name}│
        |===================================================
        """.stripMargin());

    // this is a quick fix for FIPS based tests, see CMK-20851
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
                bisect_comment: params.CIPARAM_BISECT_COMMENT,
                disable_cache: disable_cache,
                disable_signing: disable_signing,
                distro: package_distro,
                docker_tag: setup_values.docker_tag,
                download_dir: download_dir,
                edition: edition,
                fake_artifacts: fake_artifacts,
                force_build: force_build,
                // special case, this tests requires a signed package
                relative_job_name: "builders/sign-cmk-distro-package",
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

            run_relay_tests(
                branch: setup_values.safe_branch_name,
                checkout_dir: checkout_dir,
                distro: distro,
                docker_registry: DOCKER_REGISTRY,
                edition: edition,
                make_target: make_target,
                relay_image_tag: relay_image_tag,
                test_filter: params.TEST_FILTER,
                version: cmk_version_rc_aware,
            );
        }
    }
}

return this;
