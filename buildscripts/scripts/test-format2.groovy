#!groovy

/// file: test-format.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        sh("mkdir -p ${checkout_dir}/../repo_cache; mv ${checkout_dir}/../repo_cache ${checkout_dir}/repo_cache")
        inside_container() {
            sh("mv ${checkout_dir}/repo_cache ${checkout_dir}/../repo_cache")
		    sh('echo "--repository_cache=${checkout_dir}/../repo_cache/" >> .bazelrc')
            test_jenkins_helper.execute_test([
                name: "Check format",
                cmd: "bazel run //:format.check",
            ]);
            sh("mv ${checkout_dir}/../repo_cache ${checkout_dir}/repo_cache")
        }
        sh("mv ${checkout_dir}/repo_cache ${checkout_dir}/../repo_cache")
    }
}

return this;
