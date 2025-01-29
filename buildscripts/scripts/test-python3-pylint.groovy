#!groovy

/// file: test-python3-pylint.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        inside_container() {
            lock(label: "bzl_lock_${env.NODE_NAME.split('\\.')[0].split('-')[-1]}", quantity: 1, resource : null) {
                test_jenkins_helper.execute_test([
                    name       : "test-pylint",
                    cmd        : "PYLINT_ARGS=--output-format=parseable make -C tests test-pylint",
                    output_file: "pylint.txt",
                ]);
            }
            test_jenkins_helper.analyse_issues("PYLINT", "pylint.txt");
        }
    }
}

return this;
