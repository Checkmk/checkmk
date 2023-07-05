#!groovy

/// file: test-unit-test-cores.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute CMC Test") {
            dir("packages/cmc/test") {
                sh("echo nothing TODO - the file will be removed together with job");
            }
        }
    }
}
return this;
