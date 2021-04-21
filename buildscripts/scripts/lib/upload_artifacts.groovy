// library for uploading packages
package lib

def upload(Map args) {
    // needed args + desc:
    // NAME: Name of the artifact to display
    // FILE_PATH: Path where the File is stored
    // FILE_NAME: Name of the File to be uploaded
    // CMK_VERS: Version that should be uploaded
    // UPLOAD_DEST: Where shoult the packages be uploaded to
    // SHALL_PUBLISH: bool whether or not the package should be uploaded to the website
    stage(args.NAME + ' upload package') {
        def FILE_BASE = get_file_base(args.FILE_PATH)
        def ARCHIVE_BASE = get_archive_base(FILE_BASE) 
        
        if (args.SHALL_PUBLISH) {
            via_rsync(ARCHIVE_BASE, args.CMK_VERS, args.FILE_NAME, args.UPLOAD_DEST)
        } else {
            via_archive(FILE_BASE)
        }
    }
}

def get_file_base(FILE_PATH) {
    return sh(script: "dirname ${FILE_PATH}", returnStdout: true).toString().trim()
}

def get_archive_base(FILE_BASE) { 
    return sh(script: "dirname ${FILE_BASE}", returnStdout: true).toString().trim()
}

def via_rsync(ARCHIVE_BASE, CMK_VERS, FILE_NAME, UPLOAD_DEST) {
    withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
        sh """
            rsync -av --relative \
                --exclude '*dbgsym*.deb' \
                -e "ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p 52022" \
                ${ARCHIVE_BASE}/./${CMK_VERS}/${FILE_NAME} \
                ${UPLOAD_DEST}
        """
    }
}

def via_archive(FILE_BASE) {
    dir(FILE_BASE) {
        // Multiple subsequent calls overwrite the previous artifacts. For this reason
        // we always archive all available files
        archiveArtifacts("*")
    }
}

def create_and_upload_hashes(ARCHIVE_DIR, scm, SHALL_PUBLISH, UPLOAD_DEST, CMK_VERS) {
    stage("Create and upload file hashes") {
        def HASHES_PATH = ARCHIVE_DIR + "/HASHES"
        sh("cd ${ARCHIVE_DIR} ; sha256sum -- *.{tar.gz,rpm,deb,cma,cmk} | sort -k 2 > ${HASHES_PATH}")
        upload(
            NAME: "hashes",
            FILE_PATH: HASHES_PATH,
            FILE_NAME: "HASHES",
            CMK_VERS: CMK_VERS,
            UPLOAD_DEST: UPLOAD_DEST,
            SHALL_PUBLISH: SHALL_PUBLISH,
        )
    }
}

def deploy_to_website(UPLOAD_URL, CMK_VERS) {
    stage("Deploy to Website") {
        withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
            sh """
                ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p 52022 ${UPLOAD_URL} \
                    ln -sf /var/downloads/checkmk/${CMK_VERS} /smb-share-customer/checkmk
            """
        }
    }
}

return this
