#!groovy

/// file: trigger-packages.groovy

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

def build_stages(packages_file, force_build) {
    def packages = load_json(packages_file);
    def notify = load("${checkout_dir}/buildscripts/scripts/utils/notify.groovy");

    inside_container() {
        sh("make .venv")
        parallel packages.collectEntries { p ->
            [("${p.name}"): {
                stage(p.name) {
                    catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                        def job = upstream_build(
                            omit_build_venv: true,
                            download: false,
                            relative_job_name: "builders/build-cmk-package",
                            force_build: force_build,
                            dependency_paths: [p.path] + p.dependencies,
                            build_params: [
                                "PACKAGE_PATH":  p.path,
                                "SECRET_VARS": p.sec_vars.join(","),
                                "COMMAND_LINE": p.command_line,
                            ],
                            build_params_no_check: ["CUSTOM_GIT_REF": cmd_output("git rev-parse HEAD")],
                        );
                        if (!job.new_build.asBoolean()) {
                            Utils.markStageSkippedForConditional("${p.name}");
                        }
                        if (job.result != "SUCCESS") {
                            notify.notify_maintainer_of_package(p.maintainers, p.name, "${job.url}" + "console")
                            throw new Exception("Job ${p.name} failed");
                        }
                    }
                }
            }
            ]
        }
    }
}

def preparation(packages_file) {
    stage("Preparation") {
        inside_container() {
            sh("rm -rf results; mkdir results");
            sh("buildscripts/scripts/collect_packages.py packages non-free/packages > ${packages_file}");
        }
    }
}

def main() {
    check_job_parameters([
        "FORCE_BUILD",
    ]);

    dir("${checkout_dir}") {
        def results_dir = "results";
        def packages_file = "${results_dir}/packages_generated.json";

        preparation(packages_file);

        build_stages(packages_file, params.FORCE_BUILD);

        show_duration("archiveArtifacts") {
            archiveArtifacts(allowEmptyArchive: true, artifacts: 'results/*');
        }
    }
}

return this
