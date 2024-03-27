#!groovy

/// file: trigger-packages.groovy

def build_stages(packages_file) {
    def packages = load_json(packages_file);
    def package_job = "build-package"
    def notify = load("${checkout_dir}/buildscripts/scripts/utils/notify.groovy");
    def jobs = [:];

    return packages.collectEntries { p ->
        [("${p.name}"): {
            stage(p.name) {
                catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                    // TODO: Switch to ci_artifcats / fetch_artifacts
                    jobs[p.name] = build(
                        job: package_job,
                        parameters: [
                            string(name: "PACKAGE_PATH", value: p.path),
                            string(name: "SECRET_VARS", value: p.sec_vars.join(",")),
                            string(name: "COMMAND_LINE", value: p.command_line),
                            string(name: "CUSTOM_GIT_REF", value: cmd_output("git rev-parse HEAD")),
                        ],
                        propagate: false,
                    );
                    if (jobs[p.name].result != "SUCCESS") {
                        notify.notify_maintainer_of_package(p.maintainers, p.name, "${jobs[p.name].getAbsoluteUrl()}" + "console")
                        throw new Exception("Job ${p.name} failed");
                    }
                }
            }
        }
        ]
    }
}

def preparation(packages_file) {
    stage("Preparation") {
        docker.withRegistry(DOCKER_REGISTRY, "nexus") {
            docker_image_from_alias("IMAGE_TESTING").inside() {
                sh("rm -rf results; mkdir results")
                sh("buildscripts/scripts/collect_packages.py packages > ${packages_file}");
            }
        }
    }

}

def main() {
    dir("${checkout_dir}") {
        def results_dir = "results"
        def packages_file = "${results_dir}/packages_generated.json"

        preparation(packages_file)

        parallel build_stages(packages_file);

        show_duration("archiveArtifacts") {
            archiveArtifacts(allowEmptyArchive: true, artifacts: 'results/*');
        }
    }
}


return this
