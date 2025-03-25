#!groovy

/// file: test-python3-ruff.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        inside_container() {
            lock(label: "bzl_lock_${env.NODE_NAME.split('\\.')[0].split('-')[-1]}", quantity: 1, resource : null) {
                test_jenkins_helper.execute_test([
                    name       : "test-ruff",
                    cmd        : "RUFF_ARGS=--output-format=pylint make -C tests test-ruff",
                    output_file: "ruff.txt",
                ]);
            }
            test_jenkins_helper.analyse_issues("PYLINT", "ruff.txt");
        }
    }
}

return this;
