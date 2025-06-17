#!groovy

/// file: test-github-actions.groovy

def main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def safe_branch_name = versioning.safe_branch_name();

    dir("${checkout_dir}") {
        stage('Prepare checkout folder') {
            versioning.delete_non_cre_files();
        }

        targets = cmd_output(
            "grep target: .github/workflows/pr.yaml | cut -f2 -d':'"
        ).split("\n").collect({target -> target.trim()});


        targets.each({target ->
            test_jenkins_helper.execute_test([
                name: target,
                cmd: "make -C tests ${target}",
                container_name: "ubuntu-2404-${safe_branch_name}-latest",
            ]);
        })
    }
}

return this;
