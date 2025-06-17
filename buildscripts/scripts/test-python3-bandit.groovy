#!groovy

/// file: test-python3-bandit.groovy

def main() {
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

    stage('check nosec markers') {
        try {
            dir("${checkout_dir}") {
                test_jenkins_helper.execute_test([
                    name: "test-bandit-nosec-markers",
                    cmd: "make -C tests test-bandit-nosec-markers",
                ]);
            }
        } catch(Exception) {    // groovylint-disable EmptyCatchBlock
            // Don't fail the job if un-annotated markers are found.
            // Security will have to take care of those later.
            // TODO: once we have a green baseline, mark unstable if new un-annotated markers have been added:
            // unstable("failed to validate nosec marker annotations");
        }
    }
}

return this;
