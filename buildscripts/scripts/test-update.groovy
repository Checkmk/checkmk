#!groovy

/// file: test-update.groovy

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

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
        "VERSION",
        "OVERRIDE_DISTROS",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "FAKE_WINDOWS_ARTIFACTS",
    ]);

    check_environment_variables([
        "EDITION",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: true);

    def safe_branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    // When building from a git tag (VERSION != "daily"), we cannot get the branch name from the scm so used defines.make instead.
    // this is save on master as there are no tags/versions built other than daily
    def branch_name = (params.VERSION == "daily") ? safe_branch_name : branch_version;
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, params.VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def edition = params.EDITION;
    def all_distros = versioning.get_distros(override: "all");
    def distros = versioning.get_distros(edition: edition, use_case: "daily_update_tests", override: OVERRIDE_DISTROS);
    def docker_tag = versioning.select_docker_tag(
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // 'build tag'
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
    );

    def make_target = build_make_target(edition);

    print(
        """
        |===== CONFIGURATION ===============================
        |all_distros:.............. │${all_distros}│
        |distros:.................. │${distros}│
        |edition:.................. │${edition}│
        |branch_name:.............. │${branch_name}│
        |safe_branch_name:......... │${safe_branch_name}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |branch_version:........... │${branch_version}│
        |docker_tag:............... │${docker_tag}│
        |checkout_dir:............. │${checkout_dir}│
        |branch_base_folder:....... │${branch_base_folder}│
        |make_target:.............. |${make_target}|
        |===================================================
        """.stripMargin());

    def build_for_parallel = [:];
    def relative_job_name = "${branch_base_folder}/builders/test-update-single-f12less";

    def test_stages = all_distros.collectEntries { distro -> [
        ("Test ${distro}") : {
            def stepName = "Test ${distro}";
            def run_condition = distro in distros;

            /// this makes sure the whole parallel thread is marked as skipped
            if (! run_condition){
                Utils.markStageSkippedForConditional(stepName);
            }

            smart_stage(
                name: stepName,
                condition: run_condition,
                raiseOnError: true,
            ) {
                def build_instance = smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    relative_job_name: relative_job_name,
                    build_params: [
                        DISTRO: distro,
                        EDITION: edition,
                        VERSION: version,
                        CUSTOM_GIT_REF: CUSTOM_GIT_REF,
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

                copyArtifacts(
                    projectName: relative_job_name,
                    selector: specific(build_instance.getId()), // buildNumber shall be a string
                    target: "${checkout_dir}/test-results",
                    fingerprintArtifacts: true
                );
            }
        }]
    }

    def image_name = "minimal-alpine-checkmk-ci-master:latest";
    def dockerfile = "${checkout_dir}/buildscripts/scripts/Dockerfile";
    def docker_build_args = "-f ${dockerfile} .";
    def minimal_image = docker.build(image_name, docker_build_args);

    minimal_image.inside(" -v ${checkout_dir}:/checkmk") {
        currentBuild.result = parallel(test_stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }

    stage("Archive / process test reports") {
        dir("${checkout_dir}") {
            show_duration("archiveArtifacts") {
                archiveArtifacts(allowEmptyArchive: true, artifacts: "test-results/**");
            }
        }
    }
}

return this;
