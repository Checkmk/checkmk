#!groovy

/// file: test-integration-docker.groovy

def main() {
    check_job_parameters([
        "EDITION",
        "VERSION",
        "DISABLE_CACHE",
        "FAKE_WINDOWS_ARTIFACTS",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",  // the docker tag to use for building and testing, forwarded to packages build job
    ]);

    check_environment_variables([
        "INTERNAL_DEPLOY_DEST",
        "INTERNAL_DEPLOY_PORT",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def single_tests = load("${checkout_dir}/buildscripts/scripts/utils/single_tests.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: true);

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    // When building from a git tag (VERSION != "daily"), we cannot get the branch name from the scm so used defines.make instead.
    // this is save on master as there are no tags/versions built other than daily
    def branch_name = (VERSION == "daily") ? safe_branch_name : branch_version;
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, VERSION);

    def make_target = "test-docker-docker";
    def package_dir = "${checkout_dir}/downloaded_packages_for_docker_tests";
    def source_dir = package_dir + "/" + cmk_version_rc_aware;

    def edition = params.EDITION;
    def distro = "ubuntu-22.04";
    def fake_windows_artifacts = params.FAKE_WINDOWS_ARTIFACTS;

    def relative_job_name = "${branch_base_folder}/builders/build-cmk-distro-package";
    def setup_values = single_tests.common_prepare(version: VERSION, make_target: make_target, docker_tag: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD);

    stage("Prepare workspace") {
        cleanup_directory("${package_dir}");
    }

    /// In order to ensure a fixed order for stages executed in parallel,
    /// we wait an increasing amount of time (N * 100ms).
    /// Without this we end up with a capped build overview matrix in the job view (Jenkins doesn't
    /// like changing order or amount of stages, which will happen with stages started `via parallel()`
    def timeOffsetForOrder = 0;
    def stages = [
        "Build source package": {
            sleep(0.1 * timeOffsetForOrder++);
            def build_instance = null;
            smart_stage(
                name: "Build source package",
                raiseOnError: true,
            ) {
                build_instance = smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    relative_job_name: "${branch_base_folder}/builders/build-cmk-source_tgz",
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                        VERSION: params.VERSION,
                        EDITION: params.EDITION,
                        DISABLE_CACHE: params.DISABLE_CACHE,
                        FAKE_WINDOWS_ARTIFACTS: params.FAKE_WINDOWS_ARTIFACTS,
                    ],
                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                    ],
                    no_remove_others: true, // do not delete other files in the dest dir
                    download: false,    // use copyArtifacts to avoid nested directories
                );
            }
            smart_stage(
                name: "Copy artifacts",
                condition: build_instance,
                raiseOnError: true,
            ) {
                copyArtifacts(
                    projectName: "${branch_base_folder}/builders/build-cmk-source_tgz",
                    selector: specific(build_instance.getId()),
                    target: source_dir,
                    fingerprintArtifacts: true,
                );
            }
        },
        "Build Package": {
            sleep(0.1 * timeOffsetForOrder++);
            def build_instance = null;
            smart_stage(
                name: "Build Package",
                raiseOnError: true,
            ) {
                build_instance = smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    relative_job_name: "${branch_base_folder}/builders/build-cmk-distro-package",
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                        VERSION: params.VERSION,
                        EDITION: params.EDITION,
                        DISTRO: distro,
                        DISABLE_CACHE: params.DISABLE_CACHE,
                        FAKE_WINDOWS_ARTIFACTS: params.FAKE_WINDOWS_ARTIFACTS,
                    ],
                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD: setup_values.docker_tag,
                    ],
                    no_remove_others: true, // do not delete other files in the dest dir
                    download: false,    // use copyArtifacts to avoid nested directories
                );
            }
            smart_stage(
                name: "Copy artifacts",
                condition: build_instance,
                raiseOnError: true,
            ) {
                copyArtifacts(
                    projectName: "${branch_base_folder}/builders/build-cmk-distro-package",
                    selector: specific(build_instance.getId()),
                    target: source_dir,
                    fingerprintArtifacts: true,
                );
            }
        }
    ];
    inside_container_minimal(safe_branch_name: safe_branch_name) {
        currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }

    // TODO: don't run make-test-docker but use docker.inside() instead
    stage('test cmk-docker integration') {
        dir("${checkout_dir}/tests") {
            sh("make test-docker-docker WORKSPACE='${checkout_dir}' BRANCH='$branch_name' EDITION='$EDITION' VERSION='$cmk_version_rc_aware'");
        }
    }
}

return this;
