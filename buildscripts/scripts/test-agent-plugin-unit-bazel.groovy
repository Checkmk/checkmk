#!groovy

/// file: test-agent-plugin-unit-bazel.groovy

void main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "Test for remaining python versions",
            cmd: "bazel test //tests/agent-plugin-unit:supported_python_versions",
        ]);
    }
}

return this;
