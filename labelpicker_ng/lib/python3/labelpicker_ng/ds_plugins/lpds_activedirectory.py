#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#   _____  __          __  _____
#  / ____| \ \        / / |  __ \
# | (___    \ \  /\  / /  | |__) |
#  \___ \    \ \/  \/ /   |  _  /
#  ____) |    \  /\  /    | | \ \
# |_____/      \/  \/     |_|  \_\
#
# (c) 2025 SWR
# @author Frank Baier <frank.baier@swr.de>
#
from typing import List, Optional
from pydantic import BaseModel
from pprint import pformat
import ldap
from labelpicker_ng import lpb, logger, HostLabels, Host, DatasourceConfig, LabelValue, LabelKey


class LabelMapping(BaseModel):
    """
    Represents a mapping of label names, label values, and associated ad groups.

    This class is used to model the relationship between a specific label name and
    value, along with a list of advertising groups that are associated with this
    mapping. It is designed to provide an organizational structure for label-based
    grouping and retrieval.

    :ivar label_key: The key/name of the label.
    :type label_key: LabelKey
    :ivar label_value: The value associated with the label name.
    :type label_value: LabelValue
    :ivar ad_groups: A list of advertising group identifiers associated with this
        label mapping. Defaults to an empty list.
    :type ad_groups: List[str]
    """
    label_key: LabelKey
    label_value: LabelValue
    ad_groups: List[str] = []


class LdapConfig(BaseModel):
    """
    LDAP/Active Directory Verbindungs- und Suchparameter.

    :ivar ad_servers: Liste von AD/LDAP-Server-Hosts, zu denen eine Verbindung
                      aufgebaut werden soll (Failover wird versucht).
    :type ad_servers: List[Host]
    :ivar ad_bind_user: Bind-User (z. B. "CN=svc_bind,..." oder user@domain).
    :type ad_bind_user: str
    :ivar ad_bind_password: Passwort des Bind-Users.
    :type ad_bind_password: str
    :ivar ad_domain: DNS-Domäne, die zur Adressbildung der Mitglieder verwendet wird
                     (z. B. "example.org").
    :type ad_domain: str
    :ivar ad_base_dn: Basis-DN, unter dem gesucht wird (z. B. "DC=example,DC=org").
    :type ad_base_dn: str
    :ivar ad_group_filter: LDAP-Filter zur Gruppensuche; Platzhalter {group_name}
                           wird mit dem angefragten Gruppennamen ersetzt.
                           Standard: '(&(objectClass=GROUP)(cn={group_name}))'
    :type ad_group_filter: Optional[str]
    """
    ad_servers: List[Host]
    ad_bind_user: str
    ad_bind_password: str
    ad_domain: str
    ad_base_dn: str
    ad_group_filter: Optional[str] = '(&(objectClass=GROUP)(cn={group_name}))'


class ActiveDirectoryConfig(BaseModel):
    """
    Represents the configuration for integration with an Active Directory.

    This class serves to configure and manage settings for connecting to an
    Active Directory. It includes LDAP settings and mapping configurations
    necessary for establishing and maintaining a connection. Designed to
    facilitate seamless interaction with directory services.

    :ivar ldap_config: LDAP configuration details required for connecting to the
        Active Directory.
    :type ldap_config: LdapConfig
    :ivar mapping: A list of label mappings that associates directory information
        with application labels. Defaults to an empty list.
    :type mapping: List[LabelMapping]
    """
    ldap_config: LdapConfig
    mapping: List[LabelMapping] = []


class lpds_activedirectory(lpb.Strategy):
    """
    Handles communication with Active Directory (AD) servers using LDAP protocol.

    This class provides functionalities for authenticating to AD servers, querying group
    membership information, and associating host labels based on a provided configuration.
    The class uses LDAP protocols for secure and protocol-compliant operations, enabling
    interaction with AD for group-based data retrieval and processing.

    :ivar config: The configuration object containing datasource and mapping settings.
    :type config: DatasourceConfig
    :ivar activedirectory_config: Active Directory configuration derived from the input config.
    :type activedirectory_config: ActiveDirectoryConfig
    :ivar used_ldap_server: Stores the hostname of the LDAP server successfully used for authentication.
    :type used_ldap_server: str
    :ivar ad_conn: LDAP connection object for performing operations on the AD server.
    :type ad_conn: ldap.ldapobject.SimpleLDAPObject
    """
    config: DatasourceConfig
    used_ldap_server: str
    ad_conn: ldap.ldapobject.SimpleLDAPObject

    def __init__(
            self,
            config: DatasourceConfig,
            **kwargs,
    ):
        super().__init__()
        try:
            self.config = config
            self.activedirectory_config = ActiveDirectoryConfig(**config.config)
        except Exception as e:
            logger.error(f"Mo or incomplete lpds_activedirectory config found:\n{pformat(e, indent=4)}")

    def ad_auth(
            self,
    ) -> None:
        """
        Authenticate to an Active Directory (AD) LDAP server using provided credentials. This function
        attempts to establish a connection to one of the AD servers specified in the configuration.
        If authentication succeeds, it sets the active connection and the server used for the LDAP
        operations. If all attempts fail, it raises a runtime error indicating an LDAP failure.

        :raises RuntimeError: If no LDAP servers could be successfully connected to and authenticated.
        :return: None
        """
        ldap_config = self.activedirectory_config.ldap_config
        for server in ldap_config.ad_servers:
            conn = ldap.initialize('ldap://' + server)
            conn.protocol_version = 3
            conn.set_option(ldap.OPT_REFERRALS, 0)

            try:
                conn.simple_bind_s(ldap_config.ad_bind_user, ldap_config.ad_bind_password)
                self.ad_conn = conn
                self.used_ldap_server = server
                logger.debug(f"LDAP Successfully authenticated to { self.used_ldap_server}")
            except ldap.INVALID_CREDENTIALS:
                logger.error("Invalid LDAP credentials")
            except ldap.SERVER_DOWN:
                logger.error("Server not reachable or down")
            except ldap.LDAPError as e:
                logger.error("Other LDAP error", exc_info=e)
            except Exception as e:
                logger.error("Other LDAP error", exc_info=e)

            if conn and self.used_ldap_server:
                return None

        if not self.used_ldap_server:
            raise RuntimeError("***** LDAP error! *****")
        return None

    def get_group_members(
            self,
            group_name: str,
    ) -> List[str]:
        """
        Retrieve the list of members belonging to a specified Active Directory (AD) group.

        This method queries the LDAP server for a specified group name to find and return all
        members of the group. If the group exists and has members, the method retrieves and
        formats their domain-specific email addresses. If no members are found or the group
        does not exist, an empty list is returned.

        :param group_name: The name of the AD group for which members are to be retrieved.
        :type group_name: str
        :return: A list of domain-specific formatted email addresses of group members. If
                 the group has no members or does not exist, an empty list is returned.
        :rtype: List[str]
        """
        ldap_config = self.activedirectory_config.ldap_config
        members = []
        ad_filter = ldap_config.ad_group_filter.replace('{group_name}', group_name)
        result = self.ad_conn.search_s(ldap_config.ad_base_dn, ldap.SCOPE_SUBTREE, ad_filter)
        if result:
            if len(result[0]) >= 2 and 'member' in result[0][1]:
                members_tmp = result[0][1]['member']
                for m in members_tmp:
                    members.append(str(m).split(",")[0][5:].lower() + "." +ldap_config.ad_domain)
                logger.debug(f"get {len(members)} members of AD group \"{group_name}\" successfully")
                logger.debug(f"{pformat(members, indent=4)}")
                return members
            else:
                logger.debug(f"no members of AD group \"{group_name}\" found")
        return []

    def source_algorithm(
            self,
    ) -> HostLabels:
        """
        Processes a configuration object containing LDAP access information and mappings
        to gather and associate host labels based on Active Directory groups.

        :return: A dictionary mapping hosts to their associated labels.
        :rtype: HostLabels
        """
        self.ad_auth()

        collected_labels: HostLabels = {}
        for mapping in self.activedirectory_config.mapping:
            # get member of AD group
            for ad_group in mapping.ad_groups:
                group_members = self.get_group_members(ad_group)
                for host in group_members:
                    if host not in collected_labels:
                        collected_labels[host] = {}
                    k = "{}/{}".format(
                        self.config.label_prefix, mapping.label_key
                        )
                    label_value = mapping.label_value
                    collected_labels[host].update({k: label_value})
        return collected_labels


    def process_algorithm(
            self,
            source_data: HostLabels,
    ) -> HostLabels:
        """
        Processes the algorithm for transforming or extracting data based on the given
        source data and configuration. The function applies the configuration rules to
        analyze or modify the source data and returns the processed results.

        :param source_data: Input data containing host labels to be processed
        :type source_data: HostLabels
        :return: Processed host labels after algorithm application
        :rtype: HostLabels
        """
        return source_data
