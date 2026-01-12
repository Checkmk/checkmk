#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence, Set
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import partial
from pathlib import Path
from time import time as time_time
from typing import Any, Final, Literal, NotRequired, TypedDict

from pydantic import TypeAdapter

import cmk.utils.paths
from cmk.ccc.store import DimSerializer, ObjectStore
from cmk.ccc.user import UserId
from cmk.gui import userdb, utils
from cmk.gui.breadcrumb import Breadcrumb, make_simple_page_breadcrumb
from cmk.gui.config import active_config, Config
from cmk.gui.cron import CronJob, CronJobRegistry
from cmk.gui.default_permissions import PERMISSION_SECTION_GENERAL
from cmk.gui.exceptions import MKAuthException, MKInternalError, MKUserError
from cmk.gui.form_specs import DEFAULT_VALUE, parse_data_from_field_id, render_form_spec
from cmk.gui.form_specs.generators.cascading_choice_utils import (
    CascadingDataConversion,
    enable_deprecated_cascading_elements,
)
from cmk.gui.form_specs.generators.dict_to_catalog import (
    create_flat_catalog_from_dictionary,
)
from cmk.gui.form_specs.unstable import LegacyValueSpec, OptionalChoice
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _, _l
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.page_menu import (
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import PageContext, PageEndpoint, PageRegistry
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.type_defs import AnnotatedUserId, IconNames, StaticIcon, UserSpec
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.valuespec import AbsoluteDate
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1 import Message as FSMessage
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    MultilineText,
    MultipleChoice,
    MultipleChoiceElement,
    validators,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.utils.mail import default_from_address, MailString, send_mail_sendmail, set_mail_headers

type MessageMethod = Literal["gui_hint", "gui_popup", "mail", "dashlet"]
type MessageDestination = (
    Literal["all_users", "online", "admin"] | tuple[Literal["list"], Sequence[AnnotatedUserId]]
)


class MessageText(TypedDict):
    content_type: Literal["text", "html"]
    content: str


# TODO: Use e.g. pydantic to *really* parse all parts.
class Message(TypedDict):
    text: MessageText
    dest: MessageDestination
    methods: Sequence[MessageMethod]
    valid_till: int | None
    id: str
    time: int
    security: bool
    acknowledged: bool


def create_message(
    *,
    text: MessageText,
    dest: MessageDestination,
    methods: Sequence[MessageMethod],
    valid_till: int | None = None,
    time: int | None = None,
    security: bool = False,
) -> Message:
    return Message(
        text=text,
        dest=dest,
        methods=methods,
        valid_till=valid_till,
        id=utils.gen_id(),
        time=int(time_time()) if time is None else time,
        security=security,
        acknowledged=False,
    )


def register(
    page_registry: PageRegistry,
    cron_job_registry: CronJobRegistry,
) -> None:
    page_registry.register(PageEndpoint("message", page_message))
    cron_job_registry.register(
        CronJob(
            name="execute_user_messages_spool_job",
            callable=_execute_user_messages_spool_job,
            # Usually there are no spooled messages, and the job is very fast then.
            interval=timedelta(minutes=1),
        )
    )


_MESSAGES_FILENAME = "messages.mk"


def all_messages_paths() -> Iterable[Path]:
    return cmk.utils.paths.profile_dir.glob(f"*/{_MESSAGES_FILENAME}")


def _messages_path(user_id: UserId | None) -> Path:
    return (
        cmk.utils.paths.profile_dir
        / (user.ident if user_id is None else user_id)
        / _MESSAGES_FILENAME
    )


def _modify_gui_messages(
    transform: Callable[[Iterable[Message]], list[Message]],
    user_id: UserId | None = None,
) -> list[Message]:
    store = ObjectStore[list[Message]](_messages_path(user_id), serializer=DimSerializer())
    with store.locked():
        messages = store.read_obj(default=[])
        updated_messages = transform(_remove_expired(_update_validity(messages)))
        if messages != updated_messages:
            store.write_obj(updated_messages)
        return updated_messages


def _update_validity(messages: Iterable[Message]) -> list[Message]:
    duration = active_config.user_security_notification_duration
    update_existing_duration = duration.get("update_existing_duration")
    max_duration = duration.get("max_duration")
    return [
        (
            {**message, "valid_till": message["time"] + max_duration}
            if (
                message["valid_till"] is not None
                and message["security"]
                and update_existing_duration
                and max_duration is not None
            )
            else message
        )
        for message in messages
    ]


def get_gui_messages(user_id: UserId | None = None) -> list[Message]:
    return _modify_gui_messages(list, user_id)


def _remove_expired(messages: Iterable[Message]) -> list[Message]:
    now = time.time()
    return [
        message
        for message in messages
        if (valid_till := message["valid_till"]) is None or valid_till >= now
    ]


def delete_gui_message(msg_id: str) -> None:
    def keep_or_delete(message: Message) -> Message | None:
        if message["id"] != msg_id or message["security"]:
            return message
        if len(message["methods"]) != 1 and "gui_popup" in message["methods"]:
            # If "Show popup message" and other options are combined, we have only to remove the
            # popup method to avoid the popup appearing again.
            return {**message, "methods": [m for m in message["methods"] if m != "gui_popup"]}
        return None

    _modify_gui_messages(
        lambda messages: [
            updated_message
            for message in messages
            if (updated_message := keep_or_delete(message)) is not None
        ]
    )


def acknowledge_gui_message(msg_id: str | None) -> None:
    _modify_gui_messages(
        lambda messages: [
            ({**message, "acknowledged": True} if msg_id in (message["id"], None) else message)
            for message in messages
        ]
    )


def _messaging_methods() -> dict[MessageMethod, dict[str, Any]]:
    return {
        "gui_popup": {
            "title": _("Show pop-up message"),
            "confirmation_title": _("as a pop-up message"),
            "handler": _message_gui,
        },
        "gui_hint": {
            "title": _("Show hint in the 'User' menu"),
            "confirmation_title": _("as a hint in the 'User' menu"),
            "handler": _message_gui,
        },
        "mail": {
            "title": _("Send email"),
            "confirmation_title": _("as an email"),
            "handler": _message_mail,
        },
        "dashlet": {
            "title": _("Show in the dashboard element 'User messages'"),
            "confirmation_title": _("in the dashboard element 'User messages'"),
            "handler": _message_gui,
        },
    }


permission_registry.register(
    Permission(
        section=PERMISSION_SECTION_GENERAL,
        name="message",
        title=_l("Send user message"),
        description=_l(
            "This permission allows users to send messages to the users of "
            "the monitoring system using the web interface."
        ),
        defaults=["admin"],
    )
)


def page_message(ctx: PageContext) -> None:
    if not user.may("general.message"):
        raise MKAuthException(_("You are not allowed to use the message module."))

    title = _("Send user message")
    breadcrumb = make_simple_page_breadcrumb(main_menu_registry.menu_setup(), title)
    menu = _page_menu(breadcrumb)
    make_header(html, title, breadcrumb, menu)

    spec = _message_spec(ctx.config.multisite_users)

    flat_catalog = create_flat_catalog_from_dictionary(spec)

    catalog_field_id = "_message_id"
    if transactions.check_transaction():
        try:
            msg = parse_data_from_field_id(flat_catalog, catalog_field_id)
            assert isinstance(msg, dict)
            _process_message(
                create_message(
                    text=MessageText(content_type="text", content=msg["text"]),
                    dest=msg["dest"],
                    methods=msg["methods"],
                    valid_till=msg["valid_till"],
                ),
                multisite_user_ids=ctx.config.multisite_users.keys(),
            )
        except MKUserError as e:
            html.user_error(e)

    with html.form_context("message", method="POST"):
        render_form_spec(flat_catalog, catalog_field_id, DEFAULT_VALUE, False)
        html.hidden_fields()
    html.footer()


def _page_menu(breadcrumb: Breadcrumb) -> PageMenu:
    menu = make_simple_form_page_menu(
        _("Users"),
        breadcrumb,
        form_name="message",
        button_name="_save",
        save_title=_("Send message"),
    )

    menu.dropdowns.insert(
        1,
        PageMenuDropdown(
            name="related",
            title=_("Related"),
            topics=[
                PageMenuTopic(
                    title=_("Setup"),
                    entries=[
                        PageMenuEntry(
                            title=_("Users"),
                            icon_name=StaticIcon(IconNames.users),
                            item=make_simple_link("wato.py?mode=users"),
                        )
                    ],
                ),
            ],
        ),
    )

    return menu


def _message_spec(users: Mapping[str, UserSpec]) -> Dictionary:
    return Dictionary(
        custom_validate=[partial(_validate_msg, all_user_ids=map(UserId, users.keys()))],
        elements={
            "text": DictElement(
                required=True,
                parameter_form=MultilineText(
                    title=Title("Message"),
                    help_text=Help("Insert the text to be sent to all reciepents."),
                    custom_validate=[
                        validators.LengthInRange(
                            min_value=1, error_msg=FSMessage("You need to provide a text.")
                        )
                    ],
                ),
            ),
            "dest": DictElement(
                required=True,
                parameter_form=enable_deprecated_cascading_elements(
                    CascadingSingleChoice(
                        title=Title("Send message to"),
                        help_text=Help(
                            "You can send the message to a list of multiple users, which "
                            "can be chosen out of these predefined filters."
                        ),
                        elements=[
                            CascadingSingleChoiceElement(
                                name="all_users",
                                title=Title("All users"),
                                parameter_form=FixedValue(value=True, label=Label("")),
                            ),
                            CascadingSingleChoiceElement(
                                name="list",
                                title=Title("A list of specific users"),
                                parameter_form=MultipleChoice(
                                    elements=[
                                        MultipleChoiceElement(
                                            name=key,
                                            title=Title(  # astrein: disable=localization-checker
                                                value
                                            ),
                                        )
                                        for key, value in sorted(
                                            [
                                                (uid, u.get("alias", uid))
                                                for uid, u in users.items()
                                            ],
                                            key=lambda x: x[1].lower(),
                                        )
                                    ],
                                    custom_validate=[validators.LengthInRange(min_value=1)],
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                name="online",
                                title=Title("All online users"),
                                parameter_form=FixedValue(value=True, label=Label("")),
                            ),
                        ],
                    ),
                    [
                        CascadingDataConversion(
                            name_in_form_spec="all_users",
                            value_on_disk="all_users",
                            has_form_spec=False,
                        ),
                        CascadingDataConversion(
                            name_in_form_spec="online", value_on_disk="online", has_form_spec=False
                        ),
                    ],
                ),
            ),
            "methods": DictElement(
                required=True,
                parameter_form=MultipleChoice(
                    title=Title("Messaging methods"),
                    elements=[
                        MultipleChoiceElement(
                            name=k,
                            title=Title(v["title"]),  # astrein: disable=localization-checker
                        )
                        for k, v in _messaging_methods().items()
                    ],
                    prefill=DefaultValue(["gui_popup"]),
                    custom_validate=[validators.LengthInRange(min_value=1)],
                ),
            ),
            "valid_till": DictElement(
                required=True,
                parameter_form=OptionalChoice(
                    parameter_form=LegacyValueSpec.wrap(
                        AbsoluteDate(include_time=True, label=_("at"))
                    ),
                    title=Title("Message expiration"),
                    label=Label("Expire message"),
                    help_text=Help(
                        "It is possible to automatically delete messages when the "
                        "configured time is reached. This makes it possible to inform "
                        "users about a scheduled event but suppress the message "
                        "after the event has happened."
                    ),
                ),
            ),
        },
    )


def _validate_msg(msg_with_topic: Mapping[str, Any], all_user_ids: Iterable[UserId]) -> None:
    msg = msg_with_topic["topic0"]
    assert isinstance(msg, dict)
    if not msg.get("methods"):
        raise ValidationError(FSMessage("Please select at least one messaging method."))

    valid_methods = set(_messaging_methods().keys())
    for method in msg["methods"]:
        if method not in valid_methods:
            raise ValidationError(FSMessage("Invalid messaging method selected."))

    # On manually entered list of users validate the names
    if isinstance(msg["dest"], tuple) and msg["dest"][0] == "list":
        unknown_user_ids = set(msg["dest"][1]) - frozenset(all_user_ids)
        if unknown_user_ids:
            first_unknown = next(iter(unknown_user_ids))
            raise ValidationError(
                FSMessage('A user with the id "%s" does not exist.') % first_unknown
            )


def _process_message(msg: Message, multisite_user_ids: Set[str]) -> None:
    recipients, num_success, errors = send_message(msg, multisite_user_ids)
    num_recipients = len(recipients)

    message = HTML.with_escaping(_("The message has successfully been sent..."))
    message += HTMLWriter.render_br()

    parts = []
    for method in msg["methods"]:
        parts.append(
            HTMLWriter.render_li(
                _messaging_methods()[method]["confirmation_title"]
                + (
                    _(" for all recipients.")
                    if num_success[method] == num_recipients
                    else _(" for %d of %d recipients.") % (num_success[method], num_recipients)
                )
            )
        )

    message += HTMLWriter.render_ul(HTML.empty().join(parts))
    message += HTMLWriter.render_p(_("Recipients: %s") % ", ".join(recipients))
    html.show_message(message)

    if errors:
        error_message = HTML.empty()
        for method, method_errors in errors.items():
            error_message += _("Failed to send %s messages to the following users:") % method
            table_rows = HTML.empty()
            for user_id, exception in method_errors:
                table_rows += HTMLWriter.render_tr(
                    HTMLWriter.render_td(HTMLWriter.render_tt(user_id))
                    + HTMLWriter.render_td(str(exception))
                )
            error_message += HTMLWriter.render_table(table_rows) + HTMLWriter.render_br()
        html.show_error(error_message)


def send_message(
    msg: Message, multisite_user_ids: Set[str]
) -> tuple[
    Collection[UserId],
    Mapping[MessageMethod, int],
    Mapping[MessageMethod, Collection[tuple[UserId, Exception]]],
]:
    recipients = _recipients_for(msg["dest"], multisite_user_ids)
    num_success = {method: 0 for method in msg["methods"]}
    errors = dict[MessageMethod, list[tuple[UserId, Exception]]]()
    for user_id in recipients:
        for method in msg["methods"]:
            try:
                _messaging_methods()[method]["handler"](user_id, msg)
                num_success[method] += 1
            except MKInternalError as e:
                errors.setdefault(method, []).append((user_id, e))
    return recipients, num_success, errors


def _recipients_for(
    destination: MessageDestination, multisite_user_ids: Set[str]
) -> Collection[UserId]:
    match destination:
        case "all_users":
            return [UserId(s) for s in multisite_user_ids]
        case "online":
            return userdb.get_online_user_ids(datetime.now())
        case "admin":
            return [
                user_id
                for user_id, attr in userdb.load_users(lock=False).items()
                if attr.get("automation_user", False) is False and "admin" in attr.get("roles", [])
            ]
        case ("list", user_ids):
            # Although the GUI has already validated the IDs, we need some "backend validation" here
            # for e.g. the spool mechanism.
            requested_user_ids = frozenset(user_ids)
            # NOTE: It would be nice if the multisite_user_ids were a Set[UserId].
            known_user_ids = frozenset(UserId(s) for s in multisite_user_ids)
            if unknown_user_ids := requested_user_ids - known_user_ids:
                logger.warning(f"ignoring unknown user ID(s) {', '.join(unknown_user_ids)}")
            return requested_user_ids & known_user_ids
        case other:
            # assert_never(other) doesn't work here due to several mypy bugs
            raise ValueError(f"Invalid message destination {other}")


#   ---Message Plugins-------------------------------------------------------


def _message_gui(user_id: UserId, msg: Message) -> bool:
    _modify_gui_messages(
        lambda messages: msgs if msg in (msgs := list(messages)) else msgs + [msg],
        user_id,
    )
    return True


def _message_mail(user_id: UserId, msg: Message) -> bool:
    users = userdb.load_users(lock=False)
    user_spec = users.get(user_id)

    if not user_spec:
        raise MKInternalError(_("This user does not exist."))

    if not (user_email := user_spec.get("email")):
        raise MKInternalError(_("This user has no mail address configured."))

    if not (recipient_name := user_spec.get("alias")):
        recipient_name = user_id

    if user.id is None:
        raise Exception("no user ID")

    if not (sender_name := users[user.id].get("alias")):
        sender_name = user_id

    body = _("""Greetings %s,\n\n%s sent you a message: \n\n---\n%s\n---""") % (
        recipient_name,
        sender_name,
        msg["text"]["content"],
    )

    if valid_till := msg["valid_till"]:
        body += _("This message has been created at %s and is valid till %s.") % (
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(msg["time"])),
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(valid_till)),
        )

    mail = MIMEMultipart(_charset="utf-8")
    mail.attach(MIMEText(body.replace("\n", "\r\n"), "plain", _charset="utf-8"))
    reply_to = ""
    try:
        send_mail_sendmail(
            set_mail_headers(
                MailString(user_email),
                MailString("Checkmk: Message"),
                MailString(default_from_address()),
                MailString(reply_to),
                mail,
            ),
            target=MailString(user_email),
            from_address=MailString(default_from_address()),
        )
    except Exception as exc:
        raise MKInternalError(_("Mail could not be delivered: '%s'") % exc) from exc

    return True


class SpooledMessage(TypedDict):
    text: str | MessageText
    dest: MessageDestination
    methods: Sequence[MessageMethod]
    valid_till: NotRequired[int]
    time: NotRequired[int]
    security: NotRequired[bool]


_SPOOLED_MESSAGE_ADAPTER: Final = TypeAdapter(SpooledMessage)


def to_message(spooled: SpooledMessage) -> Message:
    return create_message(
        text=(
            MessageText(content_type="text", content=text)
            if isinstance(text := spooled["text"], str)
            else text
        ),
        dest=spooled["dest"],
        methods=spooled["methods"],
        valid_till=spooled.get("valid_till"),
        time=spooled.get("time"),
        security=spooled.get("security", False),
    )


def _execute_user_messages_spool_job(config: Config) -> None:
    for path in sorted(
        cmk.utils.paths.user_messages_spool_dir.glob("[!.]*"),
        key=lambda p: p.stat().st_mtime,
    ):
        try:
            message = to_message(_SPOOLED_MESSAGE_ADAPTER.validate_json(path.read_text()))
            logger.debug("unspooled user message from %s: %s", path, message)
            send_message(message, config.multisite_users.keys())
        except Exception as exc:
            logger.warning(f"ignoring spooled user message at {path}: {exc}")
        finally:
            logger.debug("removing spooled user message at %s", path)
            path.unlink()
