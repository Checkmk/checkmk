// library for uploading packages
package lib

def upload(Map args) {
    // needed args + desc:
    // NAME: Name of the artifact to display
    // FILE_PATH: Path where the File is stored
    // FILE_NAME: Name of the File to be uploaded
    // RELEASE_KEY_PATH: Path where the release key is stored
    // CMK_VERS: Version that should be uploaded
    // UPLOAD_DEST: Where shoult the packages be uploaded to
    // SHALL_PUBLISH: bool whether or not the package should be uploaded to the website
    stage(args.NAME + ' upload package') {
        def FILE_BASE = get_file_base(args.FILE_PATH)
        def ARCHIVE_BASE = get_archive_base(FILE_BASE) 
        
        if (SHALL_PUBLISH) {
            via_rsync(args.RELEASE_KEY_PATH, ARCHIVE_BASE, args.CMK_VERS, args.FILE_NAME, args.UPLOAD_DEST)
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

def via_rsync(RELEASE_KEY_PATH, ARCHIVE_BASE, CMK_VERS, FILE_NAME, UPLOAD_DEST) {
    sh """
        rsync -av --relative \
            --exclude '*dbgsym*.deb' \
            -e "ssh -o StrictHostKeyChecking=no -i ${RELEASE_KEY_PATH} -p 52022" \
            ${ARCHIVE_BASE}/./${CMK_VERS}/${FILE_NAME} \
            ${UPLOAD_DEST}
    """
}

def via_archive(FILE_BASE) {
    dir(FILE_BASE) {
        // Multiple subsequent calls overwrite the previous artifacts. For this reason
        // we always archive all available files
        archiveArtifacts("*")
    }
}

return this
