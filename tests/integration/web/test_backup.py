# encoding: utf-8

def test_backup_key_create_web(site, monkeypatch):
    if site.file_exists("etc/check_mk/backup_keys.mk"):
        site.delete_file("etc/check_mk/backup_keys.mk")

    import wato
    mode = wato.ModeBackupEditKey()

    try:
        # First create a backup key
        key_dict = mode._create_key({
            "alias": u"älias",
            "passphrase": "passphra$e",
        })

        assert site.file_exists("etc/check_mk/backup_keys.mk")

        # Then test key existance
        test_mode = wato.ModeBackupEditKey()
        keys = test_mode.load()
        assert len(keys) == 1
    finally:
        site.delete_file("etc/check_mk/backup_keys.mk")
