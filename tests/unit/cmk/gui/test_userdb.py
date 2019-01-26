import pytest  # type: ignore

from cmk.gui.valuespec import Dictionary
import cmk.gui.config as config
import cmk.gui.userdb as userdb
import cmk.gui.plugins.userdb.utils as utils
import cmk.gui.plugins.userdb.ldap_connector as ldap


def test_user_attribute_sync_plugins(monkeypatch):
    monkeypatch.setattr(config, "wato_user_attrs", [{
        'add_custom_macro': False,
        'help': u'VIP attribute',
        'name': 'vip',
        'show_in_table': False,
        'title': u'VIP',
        'topic': 'ident',
        'type': 'TextAscii',
        'user_editable': True
    }])

    monkeypatch.setattr(utils, "user_attribute_registry", utils.UserAttributeRegistry())
    monkeypatch.setattr(userdb, "user_attribute_registry", utils.user_attribute_registry)
    monkeypatch.setattr(ldap, "ldap_attribute_plugin_registry", ldap.LDAPAttributePluginRegistry())

    assert "vip" not in utils.user_attribute_registry
    assert "vip" not in ldap.ldap_attribute_plugin_registry

    userdb.update_config_based_user_attributes()

    assert "vip" in utils.user_attribute_registry
    assert "vip" in ldap.ldap_attribute_plugin_registry

    connection = ldap.LDAPUserConnector({
        "id": "ldp",
        "directory_type": ("ad", {
            "connect_to": ("fixed_list", {
                "server": "127.0.0.1",
            })
        })
    })

    ldap_plugin = ldap.ldap_attribute_plugin_registry["vip"]()
    assert ldap_plugin.title == "VIP"
    assert ldap_plugin.help == "VIP attribute"
    assert ldap_plugin.needed_attributes(connection, {"attr": "vip_attr"}) == ["vip_attr"]
    assert ldap_plugin.needed_attributes(connection, {"attr": "vip_attr"}) == ["vip_attr"]
    assert isinstance(ldap_plugin.parameters(connection), Dictionary)

    # Test removing previously registered ones
    monkeypatch.setattr(config, "wato_user_attrs", [])
    userdb.update_config_based_user_attributes()

    assert "vip" not in utils.user_attribute_registry
    assert "vip" not in ldap.ldap_attribute_plugin_registry
