from django.utils.translation import gettext_lazy as _
from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook


@hooks.register("menu_item_hook")
def register_menu():
    return MenuItemHook(
        _("Timer Paste"),
        "fas fa-clock fa-fw",
        "aa_timerpaste:list",
        navactive=["aa_timerpaste:"],
        order=150,
    )


@hooks.register("url_hook")
def register_urls():
    return UrlHook("aa_timerpaste.urls", "aa_timerpaste", r"^timerpaste/")
