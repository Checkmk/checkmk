#!groovy

/// file: test-python3-bandit.groovy

void main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-bandit",
            cmd: "BANDIT_OUTPUT_ARGS=\"-f xml -o '$WORKSPACE/bandit_results.xml'\" make -C tests test-bandit",
        ]);
    }

    stage("Archive / process test reports") {
        show_duration("archiveArtifacts") {
            archiveArtifacts("bandit_results.xml");
        }
        xunit([Custom(
            customXSL: "$JENKINS_HOME/userContent/xunit/JUnit/0.1/bandit-xunit.xsl",
            deleteOutputFiles: true,
            failIfNotNew: true,
            pattern: "bandit_results.xml",
            skipNoTestFiles: false,
            stopProcessingIfError: true
        )]);
    }
}

return this;
