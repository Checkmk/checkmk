#!groovy

/// file: test-github-actions.groovy

def main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    inside_container(
        ulimit_nofile: 1024,
        init: true,
    ) {
        dir("${checkout_dir}") {
            stage('Prepare checkout folder') {
                versioning.delete_non_cre_files();
            }
            targets = cmd_output(
                "grep target: .github/workflows/pr.yaml | cut -f2 -d':'"
            ).split("\n").collect({target -> target.trim()})
            targets.each({target ->
                stage(target) {
                    lock(label: "bzl_lock_${env.NODE_NAME.split('\\.')[0].split('-')[-1]}", quantity: 1, resource : null) {
                        sh("make -C tests ${target}");
                    }
                }
            })
        }
    }
}

return this;
