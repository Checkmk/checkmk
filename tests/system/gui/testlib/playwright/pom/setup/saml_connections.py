#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Page objects for `Setup -> Users -> SAML authentication`.

`SamlConnections` is the listing page (`mode=saml_config`); `AddSamlConnection`
is the add/edit form (`mode=edit_saml_config`) rendered from the ported SAML2
connection Form Spec (`saml2_connection_form_spec`). Used by the Form Spec
field-exposure tests and the upgraded-site run.
"""

import logging
import re
from typing import override

from playwright.sync_api import expect, Locator

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class SamlConnections(CmkPage):
    """Represent the listing page `Setup -> Users -> SAML connections`."""

    page_title = "SAML connections"
    # MainModuleSAML2 and the listing mode share this title.
    setup_menu_entry = "SAML connections"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.setup_menu(self.setup_menu_entry).click()
        self.page.wait_for_url(
            url=re.compile(re.escape("wato.py?mode=saml_config")), wait_until="load"
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(
            self.add_connection_button,
            message="Expected 'Add connection' button on the SAML connections page",
        ).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def add_connection_button(self) -> Locator:
        """The button to add a new SAML connection."""
        return self.main_area.page_menu_bar.get_by_role("link", name="Add connection")

    def open_add_connection_form(self) -> AddSamlConnection:
        """Open the 'Add SAML connection' form and return its page object."""
        logger.info("Open the 'Add SAML connection' form")
        self.add_connection_button.click()
        return AddSamlConnection(self.page, navigate_to_page=False)


class AddSamlConnection(CmkPage):
    """Represent the add/edit SAML connection form (`mode=edit_saml_config`).

    Rendered by cmk-frontend-vue from `saml2_connection_form_spec`; the section
    headers and field titles below mirror that Form Spec definition.
    """

    page_title = "SAML connection"

    # "Connection"/"Security"/"Users" are omitted as redundant: each of those
    # sections is already proven to have rendered by its own field titles below.
    # (They also occur in the page menu/breadcrumb, which no longer matters now
    # that `form` scopes containment to the Form Spec's own <form>.)
    section_headers = (
        "General properties",
        "Checkmk service provider metadata",
    )

    # Representative field titles per section (see the `Title(...)` definitions in
    # `_wato_modes.py`). Exercised for exposure rather than an exhaustive list.
    field_titles = (
        "Connection ID",
        "Name",
        "Description",
        "Comment",
        "Documentation URL",
        "Entity ID",
        "Identity provider metadata",
        "Checkmk server URL",
        "User ID attribute",
        "Full name attribute",
        "Email address attribute",
        "Contact groups",
        "Roles",
        "Certificate to sign requests (PEM)",
    )

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' (add) form", self.page_title)
        listing = SamlConnections(self.page)
        listing.add_connection_button.click()
        self.page.wait_for_url(
            url=re.compile(re.escape("wato.py?mode=edit_saml_config")), wait_until="load"
        )
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is the '%s' form", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(
            self.save_button, message="Expected a 'Save' button on the SAML connection form"
        ).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def save_button(self) -> Locator:
        """The button to save the SAML connection."""
        return self.main_area.get_suggestion("Save")

    @property
    def form(self) -> Locator:
        """The SAML connection form body.

        Scoped to the Form Spec's own ``<form>`` (``html.form_context("value_editor",
        ...)`` in ``_wato_modes.py``) rather than the main area. ``MainArea.locator()``
        with no selector falls back to ``:scope``, which on this Vue-rendered page (no
        ``iframe[name='main']``) is the whole document -- so a containment assertion
        would also see text from the always-mounted mega-menu and pass without the
        form rendering at all.
        """
        return self.main_area.locator("form[name='value_editor']")

    def assert_fields_exposed(self) -> None:
        """Assert the ported SAML2 connection Form Spec renders (CMK-35250).

        Uses substring containment on the rendered form text: it auto-waits for the
        Vue Form Spec to mount and is tolerant of the ``(required)`` suffix, info
        icons and below-the-fold sections. Containment is scoped to ``form`` (the Form
        Spec's own ``<form>``), which is what makes each title prove the field
        rendered -- several titles ("Roles", "Contact groups") also occur in the
        Setup mega-menu, so an unscoped assertion would pass on a blank page.
        The ``customer`` field is intentionally *not* asserted -- it is popped from the
        form (`for_editing.pop("customer", None)`) pending CMK-34387, so the
        customer-field half stays a residual block (see ``assert_customer_field_absent``).
        """
        for text in (*self.section_headers, *self.field_titles):
            expect(
                self.form,
                message=f"SAML Form Spec did not expose '{text}'",
            ).to_contain_text(text)

    def assert_customer_field_absent(self) -> None:
        """Assert the edition-specific ``customer`` field is not (yet) exposed.

        Encodes the CMK-34387 residual block: when the field is surfaced, this
        assertion flips and signals the customer-field coverage can be completed.
        """
        expect(
            self.form.get_by_text("Customer", exact=True),
            message="A 'Customer' field is exposed -- CMK-34387 may have landed; "
            "complete the customer-field coverage.",
        ).to_have_count(0)
