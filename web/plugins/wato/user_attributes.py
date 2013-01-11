
declare_user_attribute(
    "force_authuser",
    Checkbox(
        title = _("Visibility of Hosts/Services"),
        label = _("Only show hosts and services the user is a contact for"),
        help = _("When this option is checked, then the status GUI will only "
                 "display hosts and services that the user is a contact for - "
                 "even if he has the permission for seeing all objects."),
    ),
    permission = "general.see_all"
)

declare_user_attribute(
    "force_authuser_webservice",
    Checkbox(
        title = _("Visibility of Hosts/Services (Webservice)"),
        label = _("Export only hosts and services the user is a contact for"),
        help = _("When this option is checked, then the Multisite webservice "
                 "will only export hosts and services that the user is a contact for - "
                 "even if he has the permission for seeing all objects."),
    ),
    permission = "general.see_all"
)


