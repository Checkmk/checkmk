#!groovy

/// file: trigger-packages.groovy

def build_stages(packages_file) {
    def packages = load_json(packages_file);
    def notify = load("${checkout_dir}/buildscripts/scripts/utils/notify.groovy");

    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
        docker_reference_image().inside() {
            sh("make .venv")
            parallel packages.collectEntries { p ->
                [("${p.name}"): {
                    stage(p.name) {
                        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                            def job = upstream_build(
                                force_build: true,
                                download: false,
                                relative_job_name: "builders/build-cmk-package",
                                build_params: [
                                    "PACKAGE_PATH":  p.path,
                                    "SECRET_VARS": p.sec_vars.join(","),
                                    "COMMAND_LINE": p.command_line,
                                    "CUSTOM_GIT_REF": cmd_output("git rev-parse HEAD"),
                                ]
                            )
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
}

def preparation(packages_file) {
    stage("Preparation") {
        docker.withRegistry(DOCKER_REGISTRY, "nexus") {
            docker_reference_image().inside() {
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

        build_stages(packages_file);

        show_duration("archiveArtifacts") {
            archiveArtifacts(allowEmptyArchive: true, artifacts: 'results/*');
        }
    }
}


return this
