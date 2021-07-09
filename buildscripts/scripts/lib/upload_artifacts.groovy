// library for uploading packages
package lib

def upload(Map args) {
    // needed args + desc:
    // NAME: Name of the artifact to display
    // FILE_PATH: Path where the File is stored
    // FILE_NAME: Name of the File to be uploaded
    // CMK_VERS: Version that should be uploaded
    // UPLOAD_DEST: Where should the packages be uploaded to
    // PORT: Port fo upload dest
    stage(args.NAME + ' upload package') {
        def FILE_BASE = get_file_base(args.FILE_PATH)
        def ARCHIVE_BASE = get_archive_base(FILE_BASE) 
        
        via_rsync(ARCHIVE_BASE, args.CMK_VERS, args.FILE_NAME, args.UPLOAD_DEST, args.PORT)
    }
}

def download(DOWNLOAD_DEST, PORT, CMK_VERSION) {
    withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
        sh """
            rsync -av --relative \
                -e "ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p ${PORT}" \
                ${DOWNLOAD_DEST}/./${CMK_VERSION}/* \
                .
        """
    }
}

def get_file_base(FILE_PATH) {
    return sh(script: "dirname ${FILE_PATH}", returnStdout: true).toString().trim()
}

def get_archive_base(FILE_BASE) { 
    return sh(script: "dirname ${FILE_BASE}", returnStdout: true).toString().trim()
}

def get_file_name(FILE_PATH) { 
    return sh(script: "basename ${FILE_PATH}", returnStdout: true).toString().trim()
}

def via_rsync(ARCHIVE_BASE, CMK_VERS, FILE_NAME, UPLOAD_DEST, PORT) {
    withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
        sh """
            rsync -av --relative \
                --exclude '*dbgsym*.deb' \
                -e "ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p ${PORT}" \
                ${ARCHIVE_BASE}/./${CMK_VERS}/${FILE_NAME} \
                ${UPLOAD_DEST}
        """
    }
}

def create_and_upload_hashes(ARCHIVE_DIR, scm, UPLOAD_DEST, PORT, CMK_VERS) {
    stage("Create and upload file hashes") {
        def HASHES_PATH = ARCHIVE_DIR + "/HASHES"
        sh("cd ${ARCHIVE_DIR} ; sha256sum -- *.{tar.gz,rpm,deb,cma,cmk} | sort -k 2 > ${HASHES_PATH}")
        upload(
            NAME: "hashes",
            FILE_PATH: HASHES_PATH,
            FILE_NAME: "HASHES",
            CMK_VERS: CMK_VERS,
            UPLOAD_DEST: UPLOAD_DEST,
            PORT: PORT,
        )
    }
}

def deploy_to_website(UPLOAD_URL, PORT, CMK_VERS) {
    stage("Deploy to Website") {
        withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
            sh """
                ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY} -p ${PORT} ${UPLOAD_URL} \
                    ln -sf /var/downloads/checkmk/${CMK_VERS} /smb-share-customer/checkmk
            """
        }
    }
}

return this
