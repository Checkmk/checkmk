// The following code adds libraries to the Pipeline script
// Functions from libraries can be run by calling file-basename.functionaname()
// If you need to adjust the loading of the library, please code your changes in
// buildscripts/scripts/ on file jenkins-lib-loader/jenkins-template.groovy and run
// jenkins-lib-loader/update-jenkins-lib-loading.sh
// check the results and commit
node {
   stage('Load Jenkins Libs') {
       def LIB = [
           $class: 'GitSCM',
           branches: scm.branches,
           doGenerateSubmoduleConfigurations: scm.doGenerateSubmoduleConfigurations,
           extensions: [[$class: 'SparseCheckoutPaths', sparseCheckoutPaths: [[path: 'vars'],
                       [path: 'buildscripts/scripts/vars']]],
                       [$class: 'CloneOption', depth: 0, noTags: true, reference: '', shallow: true]],
           userRemoteConfigs: scm.userRemoteConfigs
       ]
       library identifier: 'jenkins-libs@version', retriever: legacySCM(LIB)
    }
}
// jenkins-libs loaded
