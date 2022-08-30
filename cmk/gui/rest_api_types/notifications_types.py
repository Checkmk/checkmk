#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast, ClassVar, Literal, Protocol, Type

from cmk.utils.notify_types import (
    CustomPluginName,
    NotificationPluginNameStr,
    NotifyPluginParams,
    PluginOption,
)

from cmk.gui.rest_api_types.notifications_rule_types import (
    API_AsciiMailData,
    API_CiscoData,
    API_CustomPlugin,
    API_HTMLMailData,
    API_IlertData,
    API_JiraData,
    API_MKEventData,
    API_MSTeamsData,
    API_OpsGenieIssueData,
    API_PagerDutyData,
    API_PushOverData,
    API_ServiceNowData,
    API_SignL4Data,
    API_SlackData,
    API_SmsAPIData,
    API_SmsData,
    API_SpectrumData,
    API_VictorOpsData,
    APIIlertKeyOption,
    APINotifyPlugin,
    APIOpenGenieKeyOption,
    APIPagerDutyKeyOption,
    APIPasswordOption,
    APISignL4SecretOption,
    CheckboxEmailBodyInfo,
    CheckboxHttpProxy,
    CheckboxOpsGeniePriority,
    CheckboxPushoverPriority,
    CheckboxPushoverSound,
    CheckboxSortOrder,
    CheckboxSysLogFacility,
    CheckboxURLPrefix,
    CheckboxUseSiteIDPrefix,
    CheckboxWithBoolValue,
    CheckboxWithIntValue,
    CheckboxWithListOfStrValues,
    CheckboxWithStrValue,
    EnableSyncDeliveryViaSMTP,
    FromAndToEmailFields,
    ManagementType,
    WebhookURLOption,
)

PluginParamsOrNone = NotifyPluginParams | None
PluginMkFormatType = tuple[NotificationPluginNameStr, PluginParamsOrNone]


class NotificationPlugin(Protocol):
    plugin_name: ClassVar

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> NotificationPlugin:
        raise NotImplementedError

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> NotificationPlugin:
        raise NotImplementedError

    def api_response(self) -> APINotifyPlugin:
        raise NotImplementedError

    def to_mk_file_format(self) -> PluginMkFormatType:
        raise NotImplementedError


@dataclass
class AsciiMailPlugin:
    plugin_name: ClassVar[Literal["asciimail"]] = "asciimail"
    option: PluginOption = "cancel_previous_notifications"
    from_details: FromAndToEmailFields = field(default_factory=FromAndToEmailFields)
    reply_to: FromAndToEmailFields = field(default_factory=FromAndToEmailFields)
    subject_for_host_notifications: CheckboxWithStrValue = field(
        default_factory=CheckboxWithStrValue
    )
    subject_for_service_notifications: CheckboxWithStrValue = field(
        default_factory=CheckboxWithStrValue
    )
    send_separate_notification_to_every_recipient: CheckboxWithBoolValue = field(
        default_factory=CheckboxWithBoolValue
    )
    sort_order_for_bulk_notificaions: CheckboxSortOrder = field(default_factory=CheckboxSortOrder)
    body_head_for_both_host_and_service_notifications: CheckboxWithStrValue = field(
        default_factory=CheckboxWithStrValue
    )
    body_tail_for_host_notifications: CheckboxWithStrValue = field(
        default_factory=CheckboxWithStrValue
    )
    body_tail_for_service_notifications: CheckboxWithStrValue = field(
        default_factory=CheckboxWithStrValue
    )

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> AsciiMailPlugin:
        if pluginparams is None or isinstance(pluginparams, list):
            return cls()

        return cls(
            option="create_notification_with_the_following_parameters",
            from_details=FromAndToEmailFields.from_mk_file_format(pluginparams.get("from")),
            reply_to=FromAndToEmailFields.from_mk_file_format(pluginparams.get("reply_to")),
            subject_for_host_notifications=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("host_subject")
            ),
            subject_for_service_notifications=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("service_subject")
            ),
            body_head_for_both_host_and_service_notifications=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("common_body")
            ),
            body_tail_for_host_notifications=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("host_body")
            ),
            body_tail_for_service_notifications=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("service_body")
            ),
            sort_order_for_bulk_notificaions=CheckboxSortOrder.from_mk_file_format(
                pluginparams.get("bulk_sort_order")
            ),
            send_separate_notification_to_every_recipient=CheckboxWithBoolValue.from_mk_file_format(
                pluginparams.get("disable_multiplexing"),
            ),
        )

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> AsciiMailPlugin:
        params = cast(API_AsciiMailData, incoming["plugin_params"])

        return cls(
            option=incoming["option"],
            from_details=FromAndToEmailFields.from_api_request(params["from_details"]),
            reply_to=FromAndToEmailFields.from_api_request(params["reply_to"]),
            subject_for_host_notifications=CheckboxWithStrValue.from_api_request(
                params["subject_for_host_notifications"]
            ),
            subject_for_service_notifications=CheckboxWithStrValue.from_api_request(
                params["subject_for_service_notifications"]
            ),
            send_separate_notification_to_every_recipient=CheckboxWithBoolValue.from_api_request(
                params["send_separate_notification_to_every_recipient"]
            ),
            sort_order_for_bulk_notificaions=CheckboxSortOrder.from_api_request(
                params["sort_order_for_bulk_notificaions"]
            ),
            body_head_for_both_host_and_service_notifications=CheckboxWithStrValue.from_api_request(
                params["body_head_for_both_host_and_service_notifications"]
            ),
            body_tail_for_host_notifications=CheckboxWithStrValue.from_api_request(
                params["body_tail_for_host_notifications"]
            ),
            body_tail_for_service_notifications=CheckboxWithStrValue.from_api_request(
                params["body_tail_for_service_notifications"]
            ),
        )

    def api_response(self) -> APINotifyPlugin:
        params: API_AsciiMailData = {"plugin_name": self.__class__.plugin_name}
        if self.option == "create_notification_with_the_following_parameters":
            params.update(
                {
                    "from_details": self.from_details.api_response(),
                    "reply_to": self.reply_to.api_response(),
                    "subject_for_host_notifications": self.subject_for_host_notifications.api_response(),
                    "subject_for_service_notifications": self.subject_for_service_notifications.api_response(),
                    "sort_order_for_bulk_notificaions": self.sort_order_for_bulk_notificaions.api_response(),
                    "send_separate_notification_to_every_recipient": self.send_separate_notification_to_every_recipient.api_response(),
                    "body_head_for_both_host_and_service_notifications": self.body_head_for_both_host_and_service_notifications.api_response(),
                    "body_tail_for_host_notifications": self.body_tail_for_host_notifications.api_response(),
                    "body_tail_for_service_notifications": self.body_tail_for_service_notifications.api_response(),
                }
            )
        r: APINotifyPlugin = {"option": self.option, "plugin_params": params}
        return r

    def to_mk_file_format(self) -> PluginMkFormatType:
        if self.option == "cancel_previous_notifications":
            return (self.__class__.plugin_name, None)
        r = {
            "from": self.from_details.to_mk_file_format(),
            "reply_to": self.reply_to.to_mk_file_format(),
            "host_subject": self.subject_for_host_notifications.to_mk_file_format(),
            "service_subject": self.subject_for_service_notifications.to_mk_file_format(),
            "common_body": self.body_head_for_both_host_and_service_notifications.to_mk_file_format(),
            "host_body": self.body_tail_for_host_notifications.to_mk_file_format(),
            "service_body": self.body_tail_for_service_notifications.to_mk_file_format(),
            "bulk_sort_order": self.sort_order_for_bulk_notificaions.to_mk_file_format(),
            "disable_multiplexing": self.send_separate_notification_to_every_recipient.to_mk_file_format(),
        }
        return (self.__class__.plugin_name, {k: v for k, v in r.items() if v is not None})


@dataclass
class HTMLMailPlugin:
    plugin_name: ClassVar[Literal["mail"]] = "mail"
    option: PluginOption = "cancel_previous_notifications"
    from_details: FromAndToEmailFields = field(
        default_factory=FromAndToEmailFields,
    )
    reply_to: FromAndToEmailFields = field(
        default_factory=FromAndToEmailFields,
    )
    subject_for_host_notifications: CheckboxWithStrValue = field(
        default_factory=CheckboxWithStrValue,
    )
    subject_for_service_notifications: CheckboxWithStrValue = field(
        default_factory=CheckboxWithStrValue,
    )
    send_separate_notification_to_every_recipient: CheckboxWithBoolValue = field(
        default_factory=CheckboxWithBoolValue,
    )
    sort_order_for_bulk_notificaions: CheckboxSortOrder = field(
        default_factory=CheckboxSortOrder,
    )
    insert_html_section: CheckboxWithStrValue = field(
        default_factory=CheckboxWithStrValue,
    )
    info_to_be_displayed_in_the_email_body: CheckboxEmailBodyInfo = field(
        default_factory=CheckboxEmailBodyInfo,
    )
    url_prefix_for_links_to_checkmk: CheckboxURLPrefix = field(
        default_factory=CheckboxURLPrefix,
    )
    no_floating_graphs: CheckboxWithBoolValue = field(
        default_factory=CheckboxWithBoolValue,
    )
    smtp: EnableSyncDeliveryViaSMTP = field(
        default_factory=EnableSyncDeliveryViaSMTP,
    )
    graphs_per_notification: CheckboxWithIntValue = field(
        default_factory=CheckboxWithIntValue,
    )
    notifications_with_graphs: CheckboxWithIntValue = field(
        default_factory=CheckboxWithIntValue,
    )

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> HTMLMailPlugin:
        if pluginparams is None or isinstance(pluginparams, list):
            return cls()

        return cls(
            option="create_notification_with_the_following_parameters",
            from_details=FromAndToEmailFields.from_mk_file_format(
                pluginparams.get("from"),
            ),
            reply_to=FromAndToEmailFields.from_mk_file_format(
                pluginparams.get("reply_to"),
            ),
            subject_for_host_notifications=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("host_subject"),
            ),
            subject_for_service_notifications=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("service_subject"),
            ),
            insert_html_section=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("insert_html_section")
            ),
            smtp=EnableSyncDeliveryViaSMTP.from_mk_file_format(
                pluginparams.get("smtp"),
            ),
            info_to_be_displayed_in_the_email_body=CheckboxEmailBodyInfo.from_mk_file_format(
                pluginparams.get("elements"),
            ),
            sort_order_for_bulk_notificaions=CheckboxSortOrder.from_mk_file_format(
                pluginparams.get("bulk_sort_order"),
            ),
            send_separate_notification_to_every_recipient=CheckboxWithBoolValue.from_mk_file_format(
                pluginparams.get("disable_multiplexing"),
            ),
            url_prefix_for_links_to_checkmk=CheckboxURLPrefix.from_mk_file_format(
                pluginparams.get("url_prefix"),
            ),
            no_floating_graphs=CheckboxWithBoolValue.from_mk_file_format(
                pluginparams.get("no_floating_graphs"),
            ),
            graphs_per_notification=CheckboxWithIntValue.from_mk_file_format(
                pluginparams.get("graphs_per_notification"),
            ),
            notifications_with_graphs=CheckboxWithIntValue.from_mk_file_format(
                pluginparams.get("notifications_with_graphs"),
            ),
        )

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> HTMLMailPlugin:
        params = cast(API_HTMLMailData, incoming["plugin_params"])

        return cls(
            option=incoming["option"],
            from_details=FromAndToEmailFields.from_api_request(params["from_details"]),
            reply_to=FromAndToEmailFields.from_api_request(params["reply_to"]),
            subject_for_host_notifications=CheckboxWithStrValue.from_api_request(
                params["subject_for_host_notifications"]
            ),
            subject_for_service_notifications=CheckboxWithStrValue.from_api_request(
                params["subject_for_service_notifications"]
            ),
            send_separate_notification_to_every_recipient=CheckboxWithBoolValue.from_api_request(
                params["send_separate_notification_to_every_recipient"]
            ),
            sort_order_for_bulk_notificaions=CheckboxSortOrder.from_api_request(
                params["sort_order_for_bulk_notificaions"]
            ),
            insert_html_section=CheckboxWithStrValue.from_api_request(
                params["insert_html_section_between_body_and_table"]
            ),
            info_to_be_displayed_in_the_email_body=CheckboxEmailBodyInfo.from_api_request(
                params["info_to_be_displayed_in_the_email_body"]
            ),
            url_prefix_for_links_to_checkmk=CheckboxURLPrefix.from_api_request(
                params["url_prefix_for_links_to_checkmk"]
            ),
            no_floating_graphs=CheckboxWithBoolValue.from_api_request(
                params["display_graphs_among_each_other"]
            ),
            smtp=EnableSyncDeliveryViaSMTP.from_api_request(params["enable_sync_smtp"]),
            graphs_per_notification=CheckboxWithIntValue.from_api_request(
                params["graphs_per_notification"]
            ),
            notifications_with_graphs=CheckboxWithIntValue.from_api_request(
                params["bulk_notifications_with_graphs"]
            ),
        )

    def api_response(self) -> APINotifyPlugin:
        params: API_HTMLMailData = {"plugin_name": self.__class__.plugin_name}
        if self.option == "create_notification_with_the_following_parameters":
            params.update(
                {
                    "from_details": self.from_details.api_response(),
                    "reply_to": self.reply_to.api_response(),
                    "subject_for_host_notifications": self.subject_for_host_notifications.api_response(),
                    "subject_for_service_notifications": self.subject_for_service_notifications.api_response(),
                    "info_to_be_displayed_in_the_email_body": self.info_to_be_displayed_in_the_email_body.api_response(),
                    "insert_html_section_between_body_and_table": self.insert_html_section.api_response(),
                    "url_prefix_for_links_to_checkmk": self.url_prefix_for_links_to_checkmk.api_response(),
                    "sort_order_for_bulk_notificaions": self.sort_order_for_bulk_notificaions.api_response(),
                    "send_separate_notification_to_every_recipient": self.send_separate_notification_to_every_recipient.api_response(),
                    "enable_sync_smtp": self.smtp.api_response(),
                    "display_graphs_among_each_other": self.no_floating_graphs.api_response(),
                    "graphs_per_notification": self.graphs_per_notification.api_response(),
                    "bulk_notifications_with_graphs": self.notifications_with_graphs.api_response(),
                }
            )
        r: APINotifyPlugin = {"option": self.option, "plugin_params": params}
        return r

    def to_mk_file_format(self) -> PluginMkFormatType:
        if self.option == "cancel_previous_notifications":
            return (self.__class__.plugin_name, None)
        r = {
            "from": self.from_details.to_mk_file_format(),
            "reply_to": self.reply_to.to_mk_file_format(),
            "host_subject": self.subject_for_host_notifications.to_mk_file_format(),
            "service_subject": self.subject_for_service_notifications.to_mk_file_format(),
            "disable_multiplexing": self.send_separate_notification_to_every_recipient.to_mk_file_format(),
            "url_prefix": self.url_prefix_for_links_to_checkmk.to_mk_file_format(),
            "elements": self.info_to_be_displayed_in_the_email_body.to_mk_file_format(),
            "bulk_sort_order": self.sort_order_for_bulk_notificaions.to_mk_file_format(),
            "insert_html_section": self.insert_html_section.to_mk_file_format(),
            "smtp": None if self.smtp is None else self.smtp.to_mk_file_format(),
            "graphs_per_notification": self.graphs_per_notification.to_mk_file_format(),
            "no_floating_graphs": self.no_floating_graphs.to_mk_file_format(),
            "notifications_with_graphs": self.notifications_with_graphs.to_mk_file_format(),
        }
        return (self.__class__.plugin_name, {k: v for k, v in r.items() if v is not None})


@dataclass
class CiscoWebexPlugin:
    plugin_name: ClassVar[Literal["cisco_webex_teams"]] = "cisco_webex_teams"
    option: PluginOption = "cancel_previous_notifications"
    webhook_url: WebhookURLOption = field(default_factory=WebhookURLOption)
    http_proxy: CheckboxHttpProxy = field(default_factory=CheckboxHttpProxy)
    url_prefix_for_links_to_checkmk: CheckboxURLPrefix = field(default_factory=CheckboxURLPrefix)
    disable_ssl_cert_verification: CheckboxWithBoolValue = field(
        default_factory=CheckboxWithBoolValue
    )

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> CiscoWebexPlugin:
        if pluginparams is None or isinstance(pluginparams, list):
            return cls()

        return cls(
            option="create_notification_with_the_following_parameters",
            webhook_url=WebhookURLOption.from_mk_file_format(
                pluginparams["webhook_url"],
            ),
            url_prefix_for_links_to_checkmk=CheckboxURLPrefix.from_mk_file_format(
                pluginparams.get("url_prefix"),
            ),
            disable_ssl_cert_verification=CheckboxWithBoolValue.from_mk_file_format(
                pluginparams.get("ignore_ssl")
            ),
            http_proxy=CheckboxHttpProxy.from_mk_file_format(pluginparams.get("proxy_url")),
        )

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> CiscoWebexPlugin:
        params = cast(API_CiscoData, incoming["plugin_params"])

        return cls(
            option=incoming["option"],
            webhook_url=WebhookURLOption.from_api_request((params["webhook_url"])),
            http_proxy=CheckboxHttpProxy.from_api_request(params["http_proxy"]),
            url_prefix_for_links_to_checkmk=CheckboxURLPrefix.from_api_request(
                params["url_prefix_for_links_to_checkmk"]
            ),
            disable_ssl_cert_verification=CheckboxWithBoolValue.from_api_request(
                params["disable_ssl_cert_verification"]
            ),
        )

    def api_response(self) -> APINotifyPlugin:
        params: API_CiscoData = {"plugin_name": self.__class__.plugin_name}
        if self.option == "create_notification_with_the_following_parameters":
            params.update(
                {
                    "webhook_url": self.webhook_url.api_response(),
                    "url_prefix_for_links_to_checkmk": self.url_prefix_for_links_to_checkmk.api_response(),
                    "disable_ssl_cert_verification": self.disable_ssl_cert_verification.api_response(),
                    "http_proxy": self.http_proxy.api_response(),
                }
            )
        r: APINotifyPlugin = {"option": self.option, "plugin_params": params}
        return r

    def to_mk_file_format(self) -> PluginMkFormatType:
        if self.option == "cancel_previous_notifications":
            return (self.__class__.plugin_name, None)
        r = {
            "webhook_url": self.webhook_url.to_mk_file_format(),
            "url_prefix": self.url_prefix_for_links_to_checkmk.to_mk_file_format(),
            "ignore_ssl": self.disable_ssl_cert_verification.to_mk_file_format(),
            "proxy_url": self.http_proxy.to_mk_file_format(),
        }
        return (self.__class__.plugin_name, {k: v for k, v in r.items() if v is not None})


@dataclass
class MkEventDPlugin:
    plugin_name: ClassVar[Literal["mkeventd"]] = "mkeventd"
    option: PluginOption = "cancel_previous_notifications"
    syslog_facility_to_use: CheckboxSysLogFacility = field(default_factory=CheckboxSysLogFacility)
    ip_address_of_remote_ec: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> MkEventDPlugin:
        if pluginparams is None or isinstance(pluginparams, list):
            return cls()

        return cls(
            option="create_notification_with_the_following_parameters",
            syslog_facility_to_use=CheckboxSysLogFacility.from_mk_file_format(
                pluginparams.get("facility")
            ),
            ip_address_of_remote_ec=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("remote")
            ),
        )

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> MkEventDPlugin:
        params = cast(API_MKEventData, incoming["plugin_params"])

        return cls(
            option=incoming["option"],
            syslog_facility_to_use=CheckboxSysLogFacility.from_api_request(
                params["syslog_facility_to_use"]
            ),
            ip_address_of_remote_ec=CheckboxWithStrValue.from_api_request(
                params["ip_address_of_remote_event_console"]
            ),
        )

    def api_response(self) -> APINotifyPlugin:
        params: API_MKEventData = {"plugin_name": self.__class__.plugin_name}
        if self.option == "create_notification_with_the_following_parameters":
            params.update(
                {
                    "syslog_facility_to_use": self.syslog_facility_to_use.api_response(),
                    "ip_address_of_remote_event_console": self.ip_address_of_remote_ec.api_response(),
                }
            )
        r: APINotifyPlugin = {"option": self.option, "plugin_params": params}
        return r

    def to_mk_file_format(self) -> PluginMkFormatType:
        if self.option == "cancel_previous_notifications":
            return (self.__class__.plugin_name, None)

        r = {
            "remote": self.ip_address_of_remote_ec.to_mk_file_format(),
            "facility": self.syslog_facility_to_use.to_mk_file_format(),
        }
        return (self.__class__.plugin_name, {k: v for k, v in r.items() if v is not None})


@dataclass
class IlertPlugin:
    plugin_name: ClassVar[Literal["ilert"]] = "ilert"
    option: PluginOption = "cancel_previous_notifications"
    ilert_key: APIIlertKeyOption = field(default_factory=APIIlertKeyOption)
    disable_ssl_cert_verification: CheckboxWithBoolValue = field(
        default_factory=CheckboxWithBoolValue
    )
    ilert_priority: Literal["HIGH", "LOW"] = "HIGH"
    ilert_summary_host: str = ""
    ilert_summary_service: str = ""
    http_proxy: CheckboxHttpProxy = field(default_factory=CheckboxHttpProxy)
    url_prefix_for_links_to_checkmk: CheckboxURLPrefix = field(default_factory=CheckboxURLPrefix)

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> IlertPlugin:
        if pluginparams is None or isinstance(pluginparams, list):
            return cls()

        return cls(
            option="create_notification_with_the_following_parameters",
            ilert_key=APIIlertKeyOption.from_mk_file_format(pluginparams["ilert_api_key"]),
            disable_ssl_cert_verification=CheckboxWithBoolValue.from_mk_file_format(
                pluginparams.get("ignore_ssl")
            ),
            http_proxy=CheckboxHttpProxy.from_mk_file_format(pluginparams.get("proxy_url")),
            url_prefix_for_links_to_checkmk=CheckboxURLPrefix.from_mk_file_format(
                pluginparams.get("url_prefix")
            ),
            ilert_priority=pluginparams["ilert_priority"],
            ilert_summary_host=pluginparams["ilert_summary_host"],
            ilert_summary_service=pluginparams["ilert_summary_service"],
        )

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> IlertPlugin:
        params = cast(API_IlertData, incoming["plugin_params"])

        return cls(
            option=incoming["option"],
            ilert_key=APIIlertKeyOption.from_api_request(params["api_key"]),
            disable_ssl_cert_verification=CheckboxWithBoolValue.from_api_request(
                params["disable_ssl_cert_verification"]
            ),
            ilert_priority=params["notification_priority"],
            ilert_summary_host=params["custom_summary_for_host_alerts"],
            ilert_summary_service=params["custom_summary_for_service_alerts"],
            http_proxy=CheckboxHttpProxy.from_api_request(params["http_proxy"]),
            url_prefix_for_links_to_checkmk=CheckboxURLPrefix.from_api_request(
                params["url_prefix_for_links_to_checkmk"]
            ),
        )

    def api_response(self) -> APINotifyPlugin:
        params: API_IlertData = {"plugin_name": self.__class__.plugin_name}
        if self.option == "create_notification_with_the_following_parameters":
            params.update(
                {
                    "api_key": self.ilert_key.api_response(),
                    "disable_ssl_cert_verification": self.disable_ssl_cert_verification.api_response(),
                    "notification_priority": self.ilert_priority,
                    "custom_summary_for_host_alerts": self.ilert_summary_host,
                    "custom_summary_for_service_alerts": self.ilert_summary_service,
                    "url_prefix_for_links_to_checkmk": self.url_prefix_for_links_to_checkmk.api_response(),
                    "http_proxy": self.http_proxy.api_response(),
                }
            )
        r: APINotifyPlugin = {"option": self.option, "plugin_params": params}
        return r

    def to_mk_file_format(self) -> PluginMkFormatType:
        if self.option == "cancel_previous_notifications":
            return (self.__class__.plugin_name, None)
        r = {
            "ilert_api_key": self.ilert_key.to_mk_file_format(),
            "ignore_ssl": self.disable_ssl_cert_verification.to_mk_file_format(),
            "ilert_priority": self.ilert_priority,
            "ilert_summary_host": self.ilert_summary_host,
            "ilert_summary_service": self.ilert_summary_service,
            "url_prefix": self.url_prefix_for_links_to_checkmk.to_mk_file_format(),
            "proxy_url": self.http_proxy.to_mk_file_format(),
        }
        return (self.__class__.plugin_name, {k: v for k, v in r.items() if v is not None})


@dataclass
class JiraIssuePlugin:
    plugin_name: ClassVar[Literal["jira_issues"]] = "jira_issues"
    option: PluginOption = "cancel_previous_notifications"
    url: str | None = None
    disable_ssl_cert_verification: CheckboxWithBoolValue = field(
        default_factory=CheckboxWithBoolValue
    )
    username: str | None = None
    password: str | None = None
    project_id: str | None = None
    issue_type_id: str | None = None
    host_custom_id: str | None = None
    service_custom_id: str | None = None
    monitoring: str | None = None
    site_customid: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    priority: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    host_summary: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    service_summary: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    label: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    resolution: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    timeout: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> JiraIssuePlugin:
        if pluginparams is None:
            return cls(option="cancel_previous_notifications")

        if isinstance(pluginparams, list):
            return cls(option="cancel_previous_notifications")

        return cls(
            option="create_notification_with_the_following_parameters",
            url=pluginparams["url"],
            disable_ssl_cert_verification=CheckboxWithBoolValue.from_mk_file_format(
                pluginparams.get("ignore_ssl"),
            ),
            username=pluginparams["username"],
            password=pluginparams["password"],
            project_id=pluginparams["project"],
            issue_type_id=pluginparams["issuetype"],
            host_custom_id=pluginparams["host_customid"],
            service_custom_id=pluginparams["service_customid"],
            monitoring=pluginparams["monitoring"],
            site_customid=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("site_customid"),
            ),
            priority=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("priority"),
            ),
            host_summary=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("host_summary"),
            ),
            service_summary=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("service_summary"),
            ),
            label=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("label"),
            ),
            resolution=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("resolution"),
            ),
            timeout=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("timeout"),
            ),
        )

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> JiraIssuePlugin:
        params = cast(API_JiraData, incoming["plugin_params"])

        return cls(
            option=incoming["option"],
            url=params["jira_url"],
            disable_ssl_cert_verification=CheckboxWithBoolValue.from_api_request(
                params["disable_ssl_cert_verification"]
            ),
            username=params["username"],
            password=params["password"],
            project_id=params["project_id"],
            issue_type_id=params["issue_type_id"],
            host_custom_id=params["host_custom_id"],
            service_custom_id=params["service_custom_id"],
            monitoring=params["monitoring_url"],
            site_customid=CheckboxWithStrValue.from_api_request(params["site_custom_id"]),
            priority=CheckboxWithStrValue.from_api_request(params["priority_id"]),
            host_summary=CheckboxWithStrValue.from_api_request(params["host_summary"]),
            service_summary=CheckboxWithStrValue.from_api_request(params["service_summary"]),
            label=CheckboxWithStrValue.from_api_request(params["label"]),
            resolution=CheckboxWithStrValue.from_api_request(params["resolution_id"]),
            timeout=CheckboxWithStrValue.from_api_request(params["optional_timeout"]),
        )

    def api_response(self) -> APINotifyPlugin:
        params: API_JiraData = {"plugin_name": self.__class__.plugin_name}
        if self.option == "create_notification_with_the_following_parameters":
            params.update(
                {
                    "jira_url": "" if self.url is None else self.url,
                    "disable_ssl_cert_verification": self.disable_ssl_cert_verification.api_response(),
                    "username": "" if self.username is None else self.username,
                    "password": "" if self.password is None else self.password,
                    "project_id": "" if self.project_id is None else self.project_id,
                    "issue_type_id": "" if self.issue_type_id is None else self.issue_type_id,
                    "host_custom_id": "" if self.host_custom_id is None else self.host_custom_id,
                    "service_custom_id": ""
                    if self.service_custom_id is None
                    else self.service_custom_id,
                    "monitoring_url": "" if self.monitoring is None else self.monitoring,
                    "site_custom_id": self.site_customid.api_response(),
                    "priority_id": self.priority.api_response(),
                    "host_summary": self.host_summary.api_response(),
                    "service_summary": self.service_summary.api_response(),
                    "label": self.label.api_response(),
                    "resolution_id": self.resolution.api_response(),
                    "optional_timeout": self.timeout.api_response(),
                }
            )
        r: APINotifyPlugin = {"option": self.option, "plugin_params": params}
        return r

    def to_mk_file_format(self) -> PluginMkFormatType:
        if self.option == "cancel_previous_notifications":
            return (self.__class__.plugin_name, None)
        r = {
            "url": self.url,
            "ignore_ssl": self.disable_ssl_cert_verification.to_mk_file_format(),
            "username": self.username,
            "password": self.password,
            "host_customid": self.host_custom_id,
            "issuetype": self.issue_type_id,
            "label": self.label.to_mk_file_format(),
            "monitoring": self.monitoring,
            "priority": self.priority.to_mk_file_format(),
            "project": self.project_id,
            "host_summary": self.host_summary.to_mk_file_format(),
            "service_customid": self.service_custom_id,
            "service_summary": self.service_summary.to_mk_file_format(),
            "site_customid": self.site_customid.to_mk_file_format(),
            "resolution": self.resolution.to_mk_file_format(),
            "timeout": self.timeout.to_mk_file_format(),
        }
        return (self.__class__.plugin_name, {k: v for k, v in r.items() if v is not None})


@dataclass
class OpsGenieIssuePlugin:
    plugin_name: ClassVar[Literal["opsgenie_issues"]] = "opsgenie_issues"
    option: PluginOption = "cancel_previous_notifications"
    api_key: APIOpenGenieKeyOption = field(default_factory=APIOpenGenieKeyOption)
    domain: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    http_proxy: CheckboxHttpProxy = field(default_factory=CheckboxHttpProxy)
    owner: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    source: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    priority: CheckboxOpsGeniePriority = field(default_factory=CheckboxOpsGeniePriority)
    note_created: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    note_closed: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    host_desc: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    svc_desc: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    host_msg: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    svc_msg: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    teams: CheckboxWithListOfStrValues = field(default_factory=CheckboxWithListOfStrValues)
    actions: CheckboxWithListOfStrValues = field(default_factory=CheckboxWithListOfStrValues)
    tags: CheckboxWithListOfStrValues = field(default_factory=CheckboxWithListOfStrValues)
    entity: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> OpsGenieIssuePlugin:
        if pluginparams is None or isinstance(pluginparams, list):
            return cls()

        return cls(
            option="create_notification_with_the_following_parameters",
            api_key=APIOpenGenieKeyOption.from_mk_file_format(
                pluginparams["password"],
            ),
            domain=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("url"),
            ),
            http_proxy=CheckboxHttpProxy.from_mk_file_format(
                pluginparams.get("proxy_url"),
            ),
            owner=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("owner"),
            ),
            source=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("source"),
            ),
            priority=CheckboxOpsGeniePriority.from_mk_file_format(
                pluginparams.get("priority"),
            ),
            note_created=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("note_created"),
            ),
            note_closed=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("note_closed"),
            ),
            host_desc=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("host_desc"),
            ),
            svc_desc=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("svc_desc"),
            ),
            host_msg=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("host_msg"),
            ),
            svc_msg=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("svc_msg"),
            ),
            teams=CheckboxWithListOfStrValues.from_mk_file_format(
                pluginparams.get("teams"),
            ),
            actions=CheckboxWithListOfStrValues.from_mk_file_format(
                pluginparams.get("actions"),
            ),
            tags=CheckboxWithListOfStrValues.from_mk_file_format(
                pluginparams.get("tags"),
            ),
            entity=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("entity"),
            ),
        )

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> OpsGenieIssuePlugin:
        params = cast(API_OpsGenieIssueData, incoming["plugin_params"])

        return cls(
            option=incoming["option"],
            api_key=APIOpenGenieKeyOption.from_api_request(params["api_key"]),
            domain=CheckboxWithStrValue.from_api_request(params["domain"]),
            http_proxy=CheckboxHttpProxy.from_api_request(params["http_proxy"]),
            owner=CheckboxWithStrValue.from_api_request(params["owner"]),
            source=CheckboxWithStrValue.from_api_request(params["source"]),
            priority=CheckboxOpsGeniePriority.from_api_request(params["priority"]),
            note_created=CheckboxWithStrValue.from_api_request(params["note_while_creating"]),
            note_closed=CheckboxWithStrValue.from_api_request(params["note_while_closing"]),
            host_desc=CheckboxWithStrValue.from_api_request(params["desc_for_host_alerts"]),
            svc_desc=CheckboxWithStrValue.from_api_request(params["desc_for_service_alerts"]),
            host_msg=CheckboxWithStrValue.from_api_request(params["message_for_host_alerts"]),
            svc_msg=CheckboxWithStrValue.from_api_request(params["message_for_service_alerts"]),
            teams=CheckboxWithListOfStrValues.from_api_request(params["responsible_teams"]),
            actions=CheckboxWithListOfStrValues.from_api_request(params["actions"]),
            tags=CheckboxWithListOfStrValues.from_api_request(params["tags"]),
            entity=CheckboxWithStrValue.from_api_request(params["entity"]),
        )

    def api_response(self) -> APINotifyPlugin:
        params: API_OpsGenieIssueData = {"plugin_name": self.__class__.plugin_name}
        if self.option == "create_notification_with_the_following_parameters":
            params.update(
                {
                    "api_key": self.api_key.api_response(),
                    "domain": self.domain.api_response(),
                    "http_proxy": self.http_proxy.api_response(),
                    "owner": self.owner.api_response(),
                    "source": self.source.api_response(),
                    "priority": self.priority.api_response(),
                    "note_while_creating": self.note_created.api_response(),
                    "note_while_closing": self.note_closed.api_response(),
                    "desc_for_host_alerts": self.host_desc.api_response(),
                    "desc_for_service_alerts": self.svc_desc.api_response(),
                    "message_for_host_alerts": self.host_msg.api_response(),
                    "message_for_service_alerts": self.svc_msg.api_response(),
                    "responsible_teams": self.teams.api_response(),
                    "actions": self.actions.api_response(),
                    "tags": self.tags.api_response(),
                    "entity": self.entity.api_response(),
                }
            )
        r: APINotifyPlugin = {"option": self.option, "plugin_params": params}
        return r

    def to_mk_file_format(self) -> PluginMkFormatType:
        if self.option == "cancel_previous_notifications":
            return (self.__class__.plugin_name, None)
        r = {
            "password": self.api_key.to_mk_file_format(),
            "url": self.domain.to_mk_file_format(),
            "proxy_url": self.http_proxy.to_mk_file_format(),
            "owner": self.owner.to_mk_file_format(),
            "source": self.source.to_mk_file_format(),
            "priority": self.priority.to_mk_file_format(),
            "note_created": self.note_created.to_mk_file_format(),
            "note_closed": self.note_closed.to_mk_file_format(),
            "host_desc": self.host_desc.to_mk_file_format(),
            "svc_desc": self.svc_desc.to_mk_file_format(),
            "host_msg": self.host_msg.to_mk_file_format(),
            "svc_msg": self.svc_msg.to_mk_file_format(),
            "teams": self.teams.to_mk_file_format(),
            "actions": self.actions.to_mk_file_format(),
            "tags": self.tags.to_mk_file_format(),
            "entity": self.entity.to_mk_file_format(),
        }

        return (self.__class__.plugin_name, {k: v for k, v in r.items() if v is not None})


@dataclass
class PagerDutyPlugin:
    plugin_name: ClassVar[Literal["pagerduty"]] = "pagerduty"
    option: PluginOption = "cancel_previous_notifications"
    integration_key: APIPagerDutyKeyOption = field(default_factory=APIPagerDutyKeyOption)
    disable_ssl_cert_verification: CheckboxWithBoolValue = field(
        default_factory=CheckboxWithBoolValue
    )
    http_proxy: CheckboxHttpProxy = field(default_factory=CheckboxHttpProxy)
    url_prefix_for_links_to_checkmk: CheckboxURLPrefix = field(default_factory=CheckboxURLPrefix)
    webhook_url: Literal[
        "https://events.pagerduty.com/v2/enqueue"
    ] = "https://events.pagerduty.com/v2/enqueue"

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> PagerDutyPlugin:
        if pluginparams is None or isinstance(pluginparams, list):
            return cls()

        return cls(
            option="create_notification_with_the_following_parameters",
            integration_key=APIPagerDutyKeyOption.from_mk_file_format(pluginparams["routing_key"]),
            disable_ssl_cert_verification=CheckboxWithBoolValue.from_mk_file_format(
                pluginparams.get("ignore_ssl"),
            ),
            http_proxy=CheckboxHttpProxy.from_mk_file_format(
                pluginparams.get("proxy_url"),
            ),
            url_prefix_for_links_to_checkmk=CheckboxURLPrefix.from_mk_file_format(
                pluginparams.get("url_prefix"),
            ),
        )

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> PagerDutyPlugin:
        params = cast(API_PagerDutyData, incoming["plugin_params"])

        return cls(
            option=incoming["option"],
            integration_key=APIPagerDutyKeyOption.from_api_request(params["integration_key"]),
            disable_ssl_cert_verification=CheckboxWithBoolValue.from_api_request(
                params["disable_ssl_cert_verification"]
            ),
            http_proxy=CheckboxHttpProxy.from_api_request(params["http_proxy"]),
            url_prefix_for_links_to_checkmk=CheckboxURLPrefix.from_api_request(
                params["url_prefix_for_links_to_checkmk"]
            ),
        )

    def api_response(self) -> APINotifyPlugin:
        params: API_PagerDutyData = {"plugin_name": self.__class__.plugin_name}
        if self.option == "create_notification_with_the_following_parameters":
            params.update(
                {
                    "integration_key": self.integration_key.api_response(),
                    "disable_ssl_cert_verification": self.disable_ssl_cert_verification.api_response(),
                    "http_proxy": self.http_proxy.api_response(),
                    "url_prefix_for_links_to_checkmk": self.url_prefix_for_links_to_checkmk.api_response(),
                }
            )

        r: APINotifyPlugin = {"option": self.option, "plugin_params": params}
        return r

    def to_mk_file_format(self) -> PluginMkFormatType:
        if self.option == "cancel_previous_notifications":
            return (self.__class__.plugin_name, None)
        r = {
            "ignore_ssl": self.disable_ssl_cert_verification.to_mk_file_format(),
            "proxy_url": self.http_proxy.to_mk_file_format(),
            "routing_key": self.integration_key.to_mk_file_format(),
            "url_prefix": self.url_prefix_for_links_to_checkmk.to_mk_file_format(),
            "webhook_url": self.webhook_url,
        }
        return (self.__class__.plugin_name, {k: v for k, v in r.items() if v is not None})


@dataclass
class PushOverPlugin:
    plugin_name: ClassVar[Literal["pushover"]] = "pushover"
    option: PluginOption = "cancel_previous_notifications"
    api_key: str | None = None
    user_group_key: str | None = None
    url_prefix_for_links_to_checkmk: CheckboxWithStrValue = field(
        default_factory=CheckboxWithStrValue
    )
    http_proxy: CheckboxHttpProxy = field(default_factory=CheckboxHttpProxy)
    priority: CheckboxPushoverPriority = field(default_factory=CheckboxPushoverPriority)
    sound: CheckboxPushoverSound = field(default_factory=CheckboxPushoverSound)

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> PushOverPlugin:
        if pluginparams is None or isinstance(pluginparams, list):
            return cls()

        return cls(
            option="create_notification_with_the_following_parameters",
            api_key=pluginparams["api_key"],
            user_group_key=pluginparams["recipient_key"],
            url_prefix_for_links_to_checkmk=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("url_prefix")
            ),
            http_proxy=CheckboxHttpProxy.from_mk_file_format(
                pluginparams.get("proxy_url"),
            ),
            priority=CheckboxPushoverPriority.from_mk_file_format(
                pluginparams.get("priority"),
            ),
            sound=CheckboxPushoverSound.from_mk_file_format(
                pluginparams.get("sound"),
            ),
        )

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> PushOverPlugin:
        params = cast(API_PushOverData, incoming["plugin_params"])

        return cls(
            option=incoming["option"],
            api_key=params["api_key"],
            user_group_key=params["user_group_key"],
            url_prefix_for_links_to_checkmk=CheckboxWithStrValue.from_api_request(
                params["url_prefix_for_links_to_checkmk"]
            ),
            http_proxy=CheckboxHttpProxy.from_api_request(params["http_proxy"]),
            priority=CheckboxPushoverPriority.from_api_request(params["priority"]),
            sound=CheckboxPushoverSound.from_api_request(params["sound"]),
        )

    def api_response(self) -> APINotifyPlugin:
        params: API_PushOverData = {"plugin_name": self.__class__.plugin_name}
        if self.option == "create_notification_with_the_following_parameters":
            params.update(
                {
                    "api_key": "" if self.api_key is None else self.api_key,
                    "user_group_key": "" if self.user_group_key is None else self.user_group_key,
                    "url_prefix_for_links_to_checkmk": self.url_prefix_for_links_to_checkmk.api_response(),
                    "http_proxy": self.http_proxy.api_response(),
                    "priority": self.priority.api_response(),
                    "sound": self.sound.api_response(),
                }
            )
        r: APINotifyPlugin = {"option": self.option, "plugin_params": params}
        return r

    def to_mk_file_format(self) -> PluginMkFormatType:
        if self.option == "cancel_previous_notifications":
            return (self.__class__.plugin_name, None)
        r = {
            "api_key": self.api_key,
            "priority": self.priority.to_mk_file_format(),
            "proxy_url": self.http_proxy.to_mk_file_format(),
            "recipient_key": self.user_group_key,
            "sound": self.sound.to_mk_file_format(),
            "url_prefix": self.url_prefix_for_links_to_checkmk.to_mk_file_format(),
        }
        return (self.__class__.plugin_name, {k: v for k, v in r.items() if v is not None})


@dataclass
class ServiceNowPlugin:
    plugin_name: ClassVar[Literal["servicenow"]] = "servicenow"
    option: PluginOption = "cancel_previous_notifications"
    url: str | None = None
    http_proxy: CheckboxHttpProxy = field(default_factory=CheckboxHttpProxy)
    username: str | None = None
    user_password: APIPasswordOption = field(default_factory=APIPasswordOption)
    use_site_id: CheckboxUseSiteIDPrefix = field(default_factory=CheckboxUseSiteIDPrefix)
    timeout: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    mgmt_type: ManagementType = field(default_factory=ManagementType)

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> ServiceNowPlugin:
        if pluginparams is None or isinstance(pluginparams, list):
            return cls()

        return cls(
            option="create_notification_with_the_following_parameters",
            url=pluginparams.get("url"),
            http_proxy=CheckboxHttpProxy.from_mk_file_format(
                pluginparams.get("proxy_url"),
            ),
            username=pluginparams.get("username"),
            user_password=APIPasswordOption.from_mk_file_format(pluginparams["password"]),
            use_site_id=CheckboxUseSiteIDPrefix.from_mk_file_format(
                pluginparams.get("use_site_id"),
            ),
            timeout=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("timeout"),
            ),
            mgmt_type=ManagementType.from_mk_file_format(pluginparams.get("mgmt_type")),
        )

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> ServiceNowPlugin:
        params = cast(API_ServiceNowData, incoming["plugin_params"])

        return cls(
            option=incoming["option"],
            url=params["servicenow_url"],
            http_proxy=CheckboxHttpProxy.from_api_request(params["http_proxy"]),
            username=params["username"],
            user_password=APIPasswordOption.from_api_request(params["user_password"]),
            use_site_id=CheckboxUseSiteIDPrefix.from_api_request(params["use_site_id_prefix"]),
            timeout=CheckboxWithStrValue.from_api_request(params["optional_timeout"]),
            mgmt_type=ManagementType.from_api_request(params["management_type"]),
        )

    def api_response(self) -> APINotifyPlugin:
        params: API_ServiceNowData = {"plugin_name": self.__class__.plugin_name}
        if self.option == "create_notification_with_the_following_parameters":
            params.update(
                {
                    "servicenow_url": "" if self.url is None else self.url,
                    "http_proxy": self.http_proxy.api_response(),
                    "username": "" if self.username is None else self.username,
                    "user_password": self.user_password.api_response(),
                    "use_site_id_prefix": self.use_site_id.api_response(),
                    "optional_timeout": self.timeout.api_response(),
                    "management_type": self.mgmt_type.api_response(),
                }
            )
        r: APINotifyPlugin = {"option": self.option, "plugin_params": params}
        return r

    def to_mk_file_format(self) -> PluginMkFormatType:
        if self.option == "cancel_previous_notifications":
            return (self.__class__.plugin_name, None)
        r = {
            "url": self.url,
            "proxy_url": self.http_proxy.to_mk_file_format(),
            "username": self.username,
            "password": self.user_password.to_mk_file_format(),
            "use_site_id": self.use_site_id.to_mk_file_format(),
            "timeout": self.timeout.to_mk_file_format(),
            "mgmt_type": self.mgmt_type.to_mk_file_format(),
        }
        return (self.__class__.plugin_name, {k: v for k, v in r.items() if v is not None})


@dataclass
class SignL4Plugin:
    plugin_name: ClassVar[Literal["signl4"]] = "signl4"
    option: PluginOption = "cancel_previous_notifications"
    team_secret: APISignL4SecretOption = field(default_factory=APISignL4SecretOption)
    url_prefix_for_links_to_checkmk: CheckboxURLPrefix = field(default_factory=CheckboxURLPrefix)
    disable_ssl_cert_verification: CheckboxWithBoolValue = field(
        default_factory=CheckboxWithBoolValue
    )
    http_proxy: CheckboxHttpProxy = field(default_factory=CheckboxHttpProxy)

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> SignL4Plugin:
        if pluginparams is None:
            return cls()

        if isinstance(pluginparams, list):
            return cls()

        return cls(
            option="create_notification_with_the_following_parameters",
            team_secret=APISignL4SecretOption.from_mk_file_format(pluginparams["password"]),
            url_prefix_for_links_to_checkmk=CheckboxURLPrefix.from_mk_file_format(
                pluginparams.get("url_prefix")
            ),
            disable_ssl_cert_verification=CheckboxWithBoolValue.from_mk_file_format(
                pluginparams.get("ignore_ssl")
            ),
            http_proxy=CheckboxHttpProxy.from_mk_file_format(
                pluginparams.get("proxy_url"),
            ),
        )

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> SignL4Plugin:
        params = cast(API_SignL4Data, incoming["plugin_params"])

        return cls(
            option=incoming["option"],
            team_secret=APISignL4SecretOption.from_api_request(params["team_secret"]),
            url_prefix_for_links_to_checkmk=CheckboxURLPrefix.from_api_request(
                params["url_prefix_for_links_to_checkmk"]
            ),
            disable_ssl_cert_verification=CheckboxWithBoolValue.from_api_request(
                params["disable_ssl_cert_verification"]
            ),
            http_proxy=CheckboxHttpProxy.from_api_request(params["http_proxy"]),
        )

    def api_response(self) -> APINotifyPlugin:
        params: API_SignL4Data = {"plugin_name": self.__class__.plugin_name}
        if self.option == "create_notification_with_the_following_parameters":
            params.update(
                {
                    "team_secret": self.team_secret.api_response(),
                    "url_prefix_for_links_to_checkmk": self.url_prefix_for_links_to_checkmk.api_response(),
                    "disable_ssl_cert_verification": self.disable_ssl_cert_verification.api_response(),
                    "http_proxy": self.http_proxy.api_response(),
                }
            )
        r: APINotifyPlugin = {"option": self.option, "plugin_params": params}
        return r

    def to_mk_file_format(self) -> PluginMkFormatType:
        if self.option == "cancel_previous_notifications":
            return (self.__class__.plugin_name, None)
        r = {
            "password": self.team_secret.to_mk_file_format(),
            "url_prefix": self.url_prefix_for_links_to_checkmk.to_mk_file_format(),
            "ignore_ssl": self.disable_ssl_cert_verification.to_mk_file_format(),
            "proxy_url": self.http_proxy.to_mk_file_format(),
        }
        return (self.__class__.plugin_name, {k: v for k, v in r.items() if v is not None})


@dataclass
class SlackPlugin:
    plugin_name: ClassVar[Literal["slack"]] = "slack"
    option: PluginOption = "cancel_previous_notifications"
    webhook_url: WebhookURLOption = field(default_factory=WebhookURLOption)
    url_prefix_for_links_to_checkmk: CheckboxURLPrefix = field(default_factory=CheckboxURLPrefix)
    disable_ssl_cert_verification: CheckboxWithBoolValue = field(
        default_factory=CheckboxWithBoolValue
    )
    http_proxy: CheckboxHttpProxy = field(default_factory=CheckboxHttpProxy)

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> SlackPlugin:
        if pluginparams is None or isinstance(pluginparams, list):
            return cls()

        return cls(
            option="create_notification_with_the_following_parameters",
            webhook_url=WebhookURLOption.from_mk_file_format(
                pluginparams["webhook_url"],
            ),
            url_prefix_for_links_to_checkmk=CheckboxURLPrefix.from_mk_file_format(
                pluginparams.get("url_prefix"),
            ),
            disable_ssl_cert_verification=CheckboxWithBoolValue.from_mk_file_format(
                pluginparams.get("ignore_ssl"),
            ),
            http_proxy=CheckboxHttpProxy.from_mk_file_format(
                pluginparams.get("proxy_url"),
            ),
        )

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> SlackPlugin:
        params = cast(API_SlackData, incoming["plugin_params"])

        return cls(
            option=incoming["option"],
            webhook_url=WebhookURLOption.from_api_request((params["webhook_url"])),
            url_prefix_for_links_to_checkmk=CheckboxURLPrefix.from_api_request(
                params["url_prefix_for_links_to_checkmk"]
            ),
            disable_ssl_cert_verification=CheckboxWithBoolValue.from_api_request(
                params["url_prefix_for_links_to_checkmk"]
            ),
            http_proxy=CheckboxHttpProxy.from_api_request(params["http_proxy"]),
        )

    def api_response(self) -> APINotifyPlugin:
        params: API_SlackData = {"plugin_name": self.__class__.plugin_name}
        if self.option == "create_notification_with_the_following_parameters":
            params.update(
                {
                    "webhook_url": self.webhook_url.api_response(),
                    "url_prefix_for_links_to_checkmk": self.url_prefix_for_links_to_checkmk.api_response(),
                    "disable_ssl_cert_verification": self.disable_ssl_cert_verification.api_response(),
                    "http_proxy": self.http_proxy.api_response(),
                }
            )
        r: APINotifyPlugin = {"option": self.option, "plugin_params": params}
        return r

    def to_mk_file_format(self) -> PluginMkFormatType:
        if self.option == "cancel_previous_notifications":
            return (self.__class__.plugin_name, None)
        r = {
            "webhook_url": self.webhook_url.to_mk_file_format(),
            "url_prefix": self.url_prefix_for_links_to_checkmk.to_mk_file_format(),
            "ignore_ssl": self.disable_ssl_cert_verification.to_mk_file_format(),
            "proxy_url": self.http_proxy.to_mk_file_format(),
        }
        return (self.__class__.plugin_name, {k: v for k, v in r.items() if v is not None})


@dataclass
class SMSAPIPlugin:
    plugin_name: ClassVar[Literal["sms_api"]] = "sms_api"
    option: PluginOption = "cancel_previous_notifications"
    modem_type: Literal["trb140"] = "trb140"  # Teltonika-TRB140
    modem_url: str | None = None
    disable_ssl_cert_verification: CheckboxWithBoolValue = field(
        default_factory=CheckboxWithBoolValue
    )
    http_proxy: CheckboxHttpProxy = field(default_factory=CheckboxHttpProxy)
    username: str | None = None
    user_password: APIPasswordOption = field(default_factory=APIPasswordOption)
    timeout: str | None = None

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> SMSAPIPlugin:
        if pluginparams is None or isinstance(pluginparams, list):
            return cls()

        return cls(
            option="create_notification_with_the_following_parameters",
            modem_url=pluginparams.get("url"),
            disable_ssl_cert_verification=CheckboxWithBoolValue.from_mk_file_format(
                pluginparams.get("ignore_ssl"),
            ),
            http_proxy=CheckboxHttpProxy.from_mk_file_format(
                pluginparams.get("proxy_url"),
            ),
            username=pluginparams.get("username"),
            user_password=APIPasswordOption.from_mk_file_format(pluginparams["password"]),
            timeout=pluginparams.get("timeout"),
        )

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> SMSAPIPlugin:
        params = cast(API_SmsAPIData, incoming["plugin_params"])

        return cls(
            option=incoming["option"],
            modem_url=params["modem_url"],
            disable_ssl_cert_verification=CheckboxWithBoolValue.from_api_request(
                params["disable_ssl_cert_verification"]
            ),
            http_proxy=CheckboxHttpProxy.from_api_request(params["http_proxy"]),
            username=params["username"],
            user_password=APIPasswordOption.from_api_request(params["user_password"]),
            timeout=params["timeout"],
        )

    def api_response(self) -> APINotifyPlugin:
        params: API_SmsAPIData = {"plugin_name": self.__class__.plugin_name}
        if self.option == "create_notification_with_the_following_parameters":
            params.update(
                {
                    "modem_type": self.modem_type,
                    "modem_url": "" if self.modem_url is None else self.modem_url,
                    "disable_ssl_cert_verification": self.disable_ssl_cert_verification.api_response(),
                    "http_proxy": self.http_proxy.api_response(),
                    "username": "" if self.username is None else self.username,
                    "user_password": self.user_password.api_response(),
                    "timeout": "" if self.timeout is None else self.timeout,
                }
            )
        r: APINotifyPlugin = {"option": self.option, "plugin_params": params}
        return r

    def to_mk_file_format(self) -> PluginMkFormatType:
        if self.option == "cancel_previous_notifications":
            return (self.__class__.plugin_name, None)
        r = {
            "modem_type": self.modem_type,
            "url": self.modem_url,
            "ignore_ssl": self.disable_ssl_cert_verification.to_mk_file_format(),
            "proxy_url": self.http_proxy.to_mk_file_format(),
            "username": self.username,
            "password": self.user_password.to_mk_file_format(),
            "timeout": self.timeout,
        }
        return (self.__class__.plugin_name, {k: v for k, v in r.items() if v is not None})


@dataclass
class SMSPlugin:
    plugin_name: ClassVar[Literal["sms"]] = "sms"
    option: PluginOption = "cancel_previous_notifications"
    params: list[str] | None = None

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> SMSPlugin:
        if pluginparams is None or isinstance(pluginparams, dict):
            return cls()

        return cls(
            option="create_notification_with_the_following_parameters",
            params=pluginparams,
        )

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> SMSPlugin:
        params = cast(API_SmsData, incoming["plugin_params"])
        return cls(
            option=incoming["option"],
            params=params["params"],
        )

    def api_response(self) -> APINotifyPlugin:
        params: API_SmsData = {"plugin_name": self.__class__.plugin_name}
        if self.option == "create_notification_with_the_following_parameters":
            params.update({"params": [] if self.params is None else self.params})

        r: APINotifyPlugin = {"option": self.option, "plugin_params": params}
        return r

    def to_mk_file_format(
        self,
    ) -> PluginMkFormatType:
        if self.option == "cancel_previous_notifications":
            return (self.__class__.plugin_name, None)
        return (self.__class__.plugin_name, self.params)


@dataclass
class SpectrumPlugin:
    plugin_name: ClassVar[Literal["spectrum"]] = "spectrum"
    option: PluginOption = "cancel_previous_notifications"
    baseoid: str = ""
    snmp_community: str = ""
    destination_ip: str = ""

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> SpectrumPlugin:
        if pluginparams is None or isinstance(pluginparams, list):
            return cls()

        return cls(
            option="create_notification_with_the_following_parameters",
            baseoid=pluginparams["baseoid"],
            snmp_community=pluginparams["community"],
            destination_ip=pluginparams["destination"],
        )

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> SpectrumPlugin:
        params = cast(API_SpectrumData, incoming["plugin_params"])

        return cls(
            option=incoming["option"],
            baseoid=params["base_oid"],
            snmp_community=params["snmp_community"],
            destination_ip=params["destination_ip"],
        )

    def api_response(self) -> APINotifyPlugin:
        params: API_SpectrumData = {"plugin_name": self.__class__.plugin_name}
        if self.option == "create_notification_with_the_following_parameters":
            params.update(
                {
                    "base_oid": self.baseoid,
                    "destination_ip": self.destination_ip,
                    "snmp_community": self.snmp_community,
                }
            )
        r: APINotifyPlugin = {"option": self.option, "plugin_params": params}
        return r

    def to_mk_file_format(self) -> PluginMkFormatType:
        if self.option == "cancel_previous_notifications":
            return (self.__class__.plugin_name, None)
        r = {
            "baseoid": self.baseoid,
            "community": self.snmp_community,
            "destination": self.destination_ip,
        }
        return (self.__class__.plugin_name, {k: v for k, v in r.items() if v is not None})


@dataclass
class VictoropsPlugin:
    plugin_name: ClassVar[Literal["victorops"]] = "victorops"
    option: PluginOption = "cancel_previous_notifications"
    disable_ssl_cert_verification: CheckboxWithBoolValue = field(
        default_factory=CheckboxWithBoolValue
    )
    http_proxy: CheckboxHttpProxy = field(default_factory=CheckboxHttpProxy)
    url_prefix_for_links_to_checkmk: CheckboxURLPrefix = field(default_factory=CheckboxURLPrefix)
    splunk_on_call_rest_endpoint: WebhookURLOption = field(default_factory=WebhookURLOption)

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> VictoropsPlugin:
        if pluginparams is None or isinstance(pluginparams, list):
            return cls()

        return cls(
            option="create_notification_with_the_following_parameters",
            disable_ssl_cert_verification=CheckboxWithBoolValue.from_mk_file_format(
                pluginparams.get("ignore_ssl")
            ),
            http_proxy=CheckboxHttpProxy.from_mk_file_format(
                pluginparams.get("proxy_url"),
            ),
            url_prefix_for_links_to_checkmk=CheckboxURLPrefix.from_mk_file_format(
                pluginparams.get("url_prefix")
            ),
            splunk_on_call_rest_endpoint=WebhookURLOption.from_mk_file_format(
                pluginparams["webhook_url"],
            ),
        )

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> VictoropsPlugin:
        params = cast(API_VictorOpsData, incoming["plugin_params"])

        return cls(
            option=incoming["option"],
            disable_ssl_cert_verification=CheckboxWithBoolValue.from_api_request(
                params["disable_ssl_cert_verification"]
            ),
            http_proxy=CheckboxHttpProxy.from_api_request(params["http_proxy"]),
            url_prefix_for_links_to_checkmk=CheckboxURLPrefix.from_api_request(
                params["url_prefix_for_links_to_checkmk"]
            ),
            splunk_on_call_rest_endpoint=WebhookURLOption.from_api_request(
                (params["splunk_on_call_rest_endpoint"])
            ),
        )

    def api_response(self) -> APINotifyPlugin:
        params: API_VictorOpsData = {"plugin_name": self.__class__.plugin_name}
        if self.option == "create_notification_with_the_following_parameters":
            params.update(
                {
                    "disable_ssl_cert_verification": self.disable_ssl_cert_verification.api_response(),
                    "http_proxy": self.http_proxy.api_response(),
                    "url_prefix_for_links_to_checkmk": self.url_prefix_for_links_to_checkmk.api_response(),
                    "splunk_on_call_rest_endpoint": self.splunk_on_call_rest_endpoint.api_response(),
                }
            )

        r: APINotifyPlugin = {"option": self.option, "plugin_params": params}
        return r

    def to_mk_file_format(self) -> PluginMkFormatType:
        if self.option == "cancel_previous_notifications":
            return (self.__class__.plugin_name, None)
        r = {
            "ignore_ssl": self.disable_ssl_cert_verification.to_mk_file_format(),
            "proxy_url": self.http_proxy.to_mk_file_format(),
            "url_prefix": self.url_prefix_for_links_to_checkmk.to_mk_file_format(),
            "webhook_url": self.splunk_on_call_rest_endpoint.to_mk_file_format(),
        }
        return (self.__class__.plugin_name, {k: v for k, v in r.items() if v is not None})


@dataclass
class MsTeamsPlugin:
    plugin_name: ClassVar[Literal["msteams"]] = "msteams"
    option: PluginOption = "cancel_previous_notifications"
    webhook_url: WebhookURLOption = field(default_factory=WebhookURLOption)
    http_proxy: CheckboxHttpProxy = field(default_factory=CheckboxHttpProxy)
    url_prefix_for_links_to_checkmk: CheckboxURLPrefix = field(
        default_factory=CheckboxURLPrefix,
    )
    host_title: CheckboxWithStrValue = field(
        default_factory=CheckboxWithStrValue,
    )
    service_title: CheckboxWithStrValue = field(
        default_factory=CheckboxWithStrValue,
    )
    host_summary: CheckboxWithStrValue = field(
        default_factory=CheckboxWithStrValue,
    )
    service_summary: CheckboxWithStrValue = field(
        default_factory=CheckboxWithStrValue,
    )
    host_details: CheckboxWithStrValue = field(
        default_factory=CheckboxWithStrValue,
    )
    service_details: CheckboxWithStrValue = field(
        default_factory=CheckboxWithStrValue,
    )
    show_affected_host_groups: CheckboxWithBoolValue = field(
        default_factory=CheckboxWithBoolValue,
    )

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams) -> MsTeamsPlugin:
        if pluginparams is None or isinstance(pluginparams, list):
            return cls()

        return cls(
            option="create_notification_with_the_following_parameters",
            webhook_url=WebhookURLOption.from_mk_file_format(
                pluginparams.get("webhook_url"),
            ),
            http_proxy=CheckboxHttpProxy.from_mk_file_format(
                pluginparams.get("proxy_url"),
            ),
            url_prefix_for_links_to_checkmk=CheckboxURLPrefix.from_mk_file_format(
                pluginparams.get("url_prefix")
            ),
            host_title=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("host_title"),
            ),
            service_title=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("service_title"),
            ),
            host_summary=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("host_summary"),
            ),
            service_summary=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("service_summary"),
            ),
            host_details=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("host_details"),
            ),
            service_details=CheckboxWithStrValue.from_mk_file_format(
                pluginparams.get("service_details"),
            ),
            show_affected_host_groups=CheckboxWithBoolValue.from_mk_file_format(
                pluginparams.get("affected_host_groups"),
            ),
        )

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> MsTeamsPlugin:
        params = cast(API_MSTeamsData, incoming["plugin_params"])

        return cls(
            option=incoming["option"],
            webhook_url=WebhookURLOption.from_api_request((params["webhook_url"])),
            http_proxy=CheckboxHttpProxy.from_api_request(params["http_proxy"]),
            host_title=CheckboxWithStrValue.from_api_request(params["host_title"]),
            service_title=CheckboxWithStrValue.from_api_request(params["service_title"]),
            host_summary=CheckboxWithStrValue.from_api_request(params["host_summary"]),
            service_summary=CheckboxWithStrValue.from_api_request(params["service_summary"]),
            url_prefix_for_links_to_checkmk=CheckboxURLPrefix.from_api_request(
                params["url_prefix_for_links_to_checkmk"]
            ),
            host_details=CheckboxWithStrValue.from_api_request(params["host_details"]),
            service_details=CheckboxWithStrValue.from_api_request(params["service_details"]),
            show_affected_host_groups=CheckboxWithBoolValue.from_api_request(
                params["affected_host_groups"]
            ),
        )

    def api_response(self) -> APINotifyPlugin:
        params: API_MSTeamsData = {"plugin_name": self.__class__.plugin_name}
        if self.option == "create_notification_with_the_following_parameters":
            params.update(
                {
                    "webhook_url": self.webhook_url.api_response(),
                    "http_proxy": self.http_proxy.api_response(),
                    "host_title": self.host_title.api_response(),
                    "service_title": self.service_title.api_response(),
                    "host_summary": self.host_summary.api_response(),
                    "service_summary": self.service_summary.api_response(),
                    "url_prefix_for_links_to_checkmk": self.url_prefix_for_links_to_checkmk.api_response(),
                    "host_details": self.host_details.api_response(),
                    "service_details": self.service_details.api_response(),
                    "affected_host_groups": self.show_affected_host_groups.api_response(),
                }
            )

        r: APINotifyPlugin = {"option": self.option, "plugin_params": params}
        return r

    def to_mk_file_format(self) -> PluginMkFormatType:
        if self.option == "cancel_previous_notifications":
            return (self.__class__.plugin_name, None)
        r = {
            "affected_host_groups": self.show_affected_host_groups.to_mk_file_format(),
            "host_details": self.host_details.to_mk_file_format(),
            "host_summary": self.host_summary.to_mk_file_format(),
            "host_title": self.host_title.to_mk_file_format(),
            "proxy_url": self.http_proxy.to_mk_file_format(),
            "service_details": self.service_details.to_mk_file_format(),
            "service_summary": self.service_summary.to_mk_file_format(),
            "service_title": self.service_title.to_mk_file_format(),
            "url_prefix": self.url_prefix_for_links_to_checkmk.to_mk_file_format(),
            "webhook_url": self.webhook_url.to_mk_file_format(),
        }
        return (self.__class__.plugin_name, {k: v for k, v in r.items() if v is not None})


@dataclass
class CustomPlugin:
    plugin_name: ClassVar[str] = "_custom_plugin_name"
    option: Literal[
        "create_notification_with_the_following_custom_parameters"
    ] = "create_notification_with_the_following_custom_parameters"
    custom_plugin_name: CustomPluginName = CustomPluginName("Unknown_plugin")
    plugin_params: NotifyPluginParams | None = None
    attr1: str = "attribute_1"
    attr2: str = "attribute_2"
    attr3: str = "attribute_3"

    @classmethod
    def from_mk_file_format(cls, pluginparams: NotifyPluginParams | None) -> CustomPlugin:
        return cls(plugin_params=pluginparams)

    @classmethod
    def from_api_request(cls, incoming: APINotifyPlugin) -> CustomPlugin:
        params = cast(API_CustomPlugin, incoming["plugin_params"])
        plugin_name = cast(CustomPluginName, incoming["plugin_params"]["plugin_name"])
        return cls(
            custom_plugin_name=plugin_name,
            attr1=params["attr1"],
            attr2=params["attr2"],
            attr3=params["attr3"],
        )

    def api_response(self) -> APINotifyPlugin:
        custom_params: API_CustomPlugin = {
            "plugin_name": self.custom_plugin_name,
            "attr1": self.attr1,
            "attr2": self.attr2,
            "attr3": self.attr3,
        }
        test_plugin_response: APINotifyPlugin = {
            "option": self.option,
            "plugin_params": custom_params,
        }
        return test_plugin_response

    def to_mk_file_format(self) -> tuple[NotificationPluginNameStr, NotifyPluginParams | None]:
        return self.custom_plugin_name, self.plugin_params


def plugin_selector(plugin_name: NotificationPluginNameStr) -> Type[NotificationPlugin] | None:
    match plugin_name:
        case "cisco_webex_teams":
            return CiscoWebexPlugin
        case "mkeventd":
            return MkEventDPlugin
        case "asciimail":
            return AsciiMailPlugin
        case "mail":
            return HTMLMailPlugin
        case "msteams":
            return MsTeamsPlugin
        case "ilert":
            return IlertPlugin
        case "jira_issues":
            return JiraIssuePlugin
        case "opsgenie_issues":
            return OpsGenieIssuePlugin
        case "pagerduty":
            return PagerDutyPlugin
        case "pushover":
            return PushOverPlugin
        case "servicenow":
            return ServiceNowPlugin
        case "signl4":
            return SignL4Plugin
        case "slack":
            return SlackPlugin
        case "sms_api":
            return SMSAPIPlugin
        case "sms":
            return SMSPlugin
        case "spectrum":
            return SpectrumPlugin
        case "victorops":
            return VictoropsPlugin
        case _:
            return None


def get_plugin_from_mk_file(
    notify_plugin_name: NotificationPluginNameStr,
    notifypluginparams: NotifyPluginParams | None,
) -> NotificationPlugin:
    plugin = plugin_selector(notify_plugin_name)

    if plugin is None:
        return CustomPlugin.from_mk_file_format(notifypluginparams)

    if notifypluginparams is None:
        return plugin()  # pylint: disable=not-callable

    return plugin.from_mk_file_format(notifypluginparams)


def get_plugin_from_api_request(incoming: APINotifyPlugin) -> NotificationPlugin:
    notify_plugin_name: NotificationPluginNameStr = incoming["plugin_params"]["plugin_name"]
    plugin = plugin_selector(notify_plugin_name)

    if plugin is None:
        return CustomPlugin.from_api_request(incoming)

    if incoming["option"] == "cancel_previous_notifications":
        return plugin()  # pylint: disable=not-callable

    return plugin.from_api_request(incoming)
