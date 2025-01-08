#!groovy

/// file: build-cmk-deliverables.groovy

/// Some decisions have been made in order to move forward but should be discussed:
///  - trigger agent updater builds here or in each job individually?
///  - tailor also triggers tests?
///  - abort on failures?

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils


/// Builds all artifacts used for a given Checkmk edition
def main() {
    check_job_parameters([
        ["EDITION", true],
        ["VERSION", true],  // should be deprecated
        ["OVERRIDE_DISTROS", false],
        ["USE_CASE", true],
        ["CIPARAM_OVERRIDE_DOCKER_TAG_BUILD", false],
        ["SKIP_DEPLOY_TO_WEBSITE", false],

        ["DISABLE_CACHE", false],
    ]);

    check_environment_variables([
        "INTERNAL_DEPLOY_URL",
        "INTERNAL_DEPLOY_DEST",
        "INTERNAL_DEPLOY_PORT",
        "DOCKER_REGISTRY",
        "NEXUS_BUILD_CACHE_URL",
        "BAZEL_CACHE_URL",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy");

    /// Might also be taken from editions.yml - there we also have "saas" and "raw" but
    /// AFAIK there is no way to extract the editions we want to test generically, so we
    /// hard-code these:
    def all_distros = versioning.get_distros(override: "all");
    def selected_distros = versioning.get_distros(
        edition: params.EDITION,
        use_case: params.USE_CASE,
        override: params.OVERRIDE_DISTROS);
    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def project_name_components = currentBuild.fullProjectName.split("/").toList();
    def branch_base_folder = project_name_components[0..project_name_components.indexOf('checkmk') + 1].join('/');

    def cmk_version_rc_aware = versioning.get_cmk_version(
        versioning.safe_branch_name(scm),
        versioning.get_branch_version(checkout_dir),
        params.VERSION
    );
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);
    def relative_deliverables_dir = "deliverables/${cmk_version_rc_aware}";
    def deliverables_dir = "${WORKSPACE}/deliverables/${cmk_version_rc_aware}";

    def upload_to_testbuilds = ! branch_base_folder.startsWith("Testing");
    def deploy_to_website = ! params.SKIP_DEPLOY_TO_WEBSITE;

    print(
        """
        |===== CONFIGURATION ===============================
        |all_distros:....................... │${all_distros}│
        |selected_distros:.................. │${selected_distros}│
        |EDITION:........................... │${params.EDITION}│
        |VERSION:........................... │${params.VERSION}│
        |USE_CASE:.......................... │${params.USE_CASE}│
        |CIPARAM_OVERRIDE_DOCKER_TAG_BUILD:. │${params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD}│
        |SKIP_DEPLOY_TO_WEBSITE:............ │${params.SKIP_DEPLOY_TO_WEBSITE}│
        |cmk_version:....................... │${cmk_version}│
        |cmk_version_rc_aware:.............. │${cmk_version_rc_aware}│
        |deploy_to_website:................. │${deploy_to_website}│
        |upload_to_testbuilds:.............. │${upload_to_testbuilds}│
        |branch_base_folder:................ │${branch_base_folder}│
        |===================================================
        """.stripMargin());

    def offsetForOrder = 0;

    def stages = [
        "Build source package": {
            sleep(0.1 * offsetForOrder++);

            smart_stage(
                name: "Build source package",
                raiseOnError: false,
            ) {
                def build_instance = smart_build(
                    job: "${branch_base_folder}/builders/build-cmk-source_tgz",
                    parameters: [
                        stringParam(name: "EDITION", value: params.EDITION),
                        stringParam(name: "VERSION", value: params.VERSION),

                        // default parameters
                        stringParam(name: "CUSTOM_GIT_REF", value: effective_git_ref),
                        booleanParam(name: "DISABLE_CACHE", value: params.DISABLE_CACHE),
                        stringParam(name: "CIPARAM_OVERRIDE_BUILD_NODE", value: params.CIPARAM_OVERRIDE_BUILD_NODE),
                        stringParam(name: "CIPARAM_CLEANUP_WORKSPACE", value: params.CIPARAM_CLEANUP_WORKSPACE),
                    ]
                );
                copyArtifacts(
                    projectName: build_instance.getFullProjectName(),
                    selector: specific(build_instance.getId()),
                    target: relative_deliverables_dir,
                    fingerprintArtifacts: true,
                )
            }
        },
        "Build BOM": {
            sleep(0.1 * offsetForOrder++);

            smart_stage(
                name: "Build BOM",
                raiseOnError: false,
            ) {
                smart_build(
                    job: "${branch_base_folder}/builders/build-cmk-bom",
                    parameters: [
                        stringParam(name: "VERSION", value: params.VERSION),

                        // default parameters
                        stringParam(name: "CUSTOM_GIT_REF", value: effective_git_ref),
                        booleanParam(name: "DISABLE_CACHE", value: params.DISABLE_CACHE),
                        stringParam(name: "CIPARAM_OVERRIDE_BUILD_NODE", value: params.CIPARAM_OVERRIDE_BUILD_NODE),
                        stringParam(name: "CIPARAM_CLEANUP_WORKSPACE", value: params.CIPARAM_CLEANUP_WORKSPACE),
                    ]
                );
            }
        }
    ];

    stages += all_distros.collectEntries { distro -> [
        ("${distro}") : {
            sleep(0.1 * offsetForOrder++);

            def run_condition = distro in selected_distros;
            /// this makes sure the whole parallel thread is marked as skipped
            if (! run_condition){
                Utils.markStageSkippedForConditional("${distro}");
            }
            smart_stage(
                name: "distro package ${distro}",
                condition: run_condition,
                raiseOnError: false,
            ) {
                def build_instance = smart_build(
                    job: "${branch_base_folder}/builders/build-cmk-distro-package",
                    parameters: [
                        stringParam(name: "EDITION", value: params.EDITION),
                        stringParam(name: "DISTRO", value: distro),
                        stringParam(name: "VERSION", value: params.VERSION),
                        stringParam(name: "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD", value: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD),

                        // default parameters
                        stringParam(name: "CUSTOM_GIT_REF", value: effective_git_ref),
                        booleanParam(name: "DISABLE_CACHE", value: params.DISABLE_CACHE),
                        stringParam(name: "CIPARAM_OVERRIDE_BUILD_NODE", value: params.CIPARAM_OVERRIDE_BUILD_NODE),
                        stringParam(name: "CIPARAM_CLEANUP_WORKSPACE", value: params.CIPARAM_CLEANUP_WORKSPACE),
                    ]
                );
                copyArtifacts(
                    projectName: build_instance.getFullProjectName(),
                    selector: specific(build_instance.getId()),
                    target: relative_deliverables_dir,
                    fingerprintArtifacts: true,
                )
            }
        }]
    }

    currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";

    smart_stage(name: "Archive artifacts") {
        dir("${deliverables_dir}") {
            show_duration("archiveArtifacts") {
                archiveArtifacts(
                    artifacts: "*.deb,*.rpm,*.cma,*.tar.gz",
                    fingerprint: true,
                );
            }
        }
    }

    smart_stage(
        name: "Upload artifacts",
        condition: upload_to_testbuilds,
    ) {
        currentBuild.description += """\
            <p><a href='${INTERNAL_DEPLOY_URL}/${cmk_version}'>Download Artifacts</a></p>
            """.stripIndent();

        // this must not be called from within the container (results in yaml package missing)
        def exclude_pattern = versioning.get_internal_artifacts_pattern();
        inside_container(ulimit_nofile: 1024) {
            artifacts_helper.upload_version_dir(
                deliverables_dir,
                WEB_DEPLOY_DEST,
                WEB_DEPLOY_PORT,
                EXCLUDE_PATTERN=exclude_pattern,
            );

            if (EDITION.toLowerCase() == "saas" && versioning.is_official_release(cmk_version_rc_aware)) {
                // check-mk-saas-2.3.0p17.cse.tar.gz + .hash
                artifacts_helper.upload_files_to_nexus(
                    "${deliverables_dir}/check-mk-saas-${cmk_version}*",
                    "${ARTIFACT_STORAGE}/repository/saas-patch-releases/",
                );
            }
        }
    }

    smart_stage(
        name: "Deploy to website",
        condition: upload_to_testbuilds && deploy_to_website,
    ) {
        inside_container(ulimit_nofile: 1024) {
            artifacts_helper.deploy_to_website(
                cmk_version_rc_aware
            );
        }
    }

    smart_stage(name: "Cleanup leftovers") {
        sh("rm -rf ${WORKSPACE}/deliverables");
    }
}

return this;
