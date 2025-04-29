#!groovy

/// file: winagt-test-integration.groovy

def main() {
    def windows = load("${checkout_dir}/buildscripts/scripts/utils/windows.groovy");

    stage("Run 'test_integration'") {
        dir("${checkout_dir}") {
            withCredentials([usernamePassword(
                    credentialsId: 'nexus',
                    passwordVariable: 'NEXUS_PASSWORD',
                    usernameVariable: 'NEXUS_USERNAME')]) {
                windows.build(
                    TARGET: 'test_integration',
                    CREDS: NEXUS_USERNAME+':'+NEXUS_PASSWORD,
                    CACHE_URL: 'https://artifacts.lan.tribe29.com/repository/omd-build-cache/'
                );
            }
        }
    }
}

return this;
