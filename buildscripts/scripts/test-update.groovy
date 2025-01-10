#!groovy

/// file: test-update.groovy

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

def main() {
    check_job_parameters([
        "VERSION",
        "OVERRIDE_DISTROS",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
    ]);

    check_environment_variables([
        "EDITION",
        "CROSS_EDITION_TARGET",
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

    def cross_edition_target = params.CROSS_EDITION_TARGET ?: "";

    print(
        """
        |===== CONFIGURATION ===============================
        |distros:.................. │${distros}│
        |all_distros:.............. │${all_distros}│
        |edition:.................. │${edition}│
        |cross_edition_target:..... │${cross_edition_target}│
        |branch_name:.............. │${branch_name}│
        |safe_branch_name:......... │${safe_branch_name}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |branch_version:........... │${branch_version}│
        |docker_tag:............... │${docker_tag}│
        |cross_edition_target:..... │${cross_edition_target}|
        |checkout_dir:............. │${checkout_dir}│
        |branch_base_folder:....... │${branch_base_folder}│
        |===================================================
        """.stripMargin());

    def build_for_parallel = [:];
    def relative_job_name = "${branch_base_folder}/builders/test-update-single-f12less";
    currentBuild.result = parallel(
        all_distros.collectEntries { distro ->
            [("${distro}") : {
                def stepName = "Test ${distro}";
                def run_condition = distro in distros;

                if (cross_edition_target && distro != "ubuntu-22.04") {
                    // see CMK-18366
                    run_condition = false;
                }

                /// this makes sure the whole parallel thread is marked as skipped
                if (! run_condition){
                    Utils.markStageSkippedForConditional(stepName);
                }

                smart_stage(
                    name: stepName,
                    condition: run_condition,
                    raiseOnError: true,
                ) {
                    def job = smart_build(
                        job: relative_job_name,
                        parameters: [
                            stringParam(name: "DISTRO", value: distro),
                            stringParam(name: "EDITION", value: edition),
                            stringParam(name: "VERSION", value: version),
                            stringParam(name: "DOCKER_TAG", value: docker_tag),
                            stringParam(name: "CROSS_EDITION_TARGET", value: cross_edition_target),
                            stringParam(name: "CUSTOM_GIT_REF", value: CUSTOM_GIT_REF),
                            stringParam(name: "CIPARAM_OVERRIDE_BUILD_NODE", value: CIPARAM_OVERRIDE_BUILD_NODE),
                            stringParam(name: "CIPARAM_CLEANUP_WORKSPACE", value: CIPARAM_CLEANUP_WORKSPACE),
                            stringParam(name: "CIPARAM_BISECT_COMMENT", value: params.CIPARAM_BISECT_COMMENT),
                        ],
                    );

                    copyArtifacts(
                        projectName: relative_job_name,
                        selector: specific(job.getId()), // buildNumber shall be a string
                        target: "${checkout_dir}/test-results",
                        fingerprintArtifacts: true
                    );
                }
            }]
        }
    ).values().every { it } ? "SUCCESS" : "FAILURE";

    stage("Archive / process test reports") {
        dir("${checkout_dir}") {
            show_duration("archiveArtifacts") {
                archiveArtifacts(allowEmptyArchive: true, artifacts: "test-results/**");
            }
            xunit([Custom(
                customXSL: "$JENKINS_HOME/userContent/xunit/JUnit/0.1/pytest-xunit.xsl",
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
