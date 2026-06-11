import pytest

from citadel.i18n import t
from citadel.i18n.translator import Translator


def test_translator_loads_catalogs():
    translator = Translator()

    assert "en" in translator.catalogs
    assert "de" in translator.catalogs
    assert translator.catalogs["en"]["room"]["enter"]
    assert translator.catalogs["de"]["room"]["enter"]


def test_translator_uses_default_german_locale():
    translator = Translator(default_locale="de")

    assert translator.t("room.enter", room="Lobby") == (
        "Willkommen im Raum 'Lobby'."
    )


def test_translator_can_use_english_locale():
    translator = Translator(default_locale="de")

    assert translator.t("room.enter", locale="en", room="Lobby") == (
        "Welcome to the 'Lobby' room."
    )


def test_module_shorthand_uses_default_german_locale():
    assert t("room.enter", room="Lobby") == "Willkommen im Raum 'Lobby'."


def test_missing_key_returns_key_in_fail_soft_mode():
    translator = Translator()

    assert translator.t("nonexistent.key") == "nonexistent.key"


def test_missing_key_raises_in_strict_mode():
    translator = Translator(strict=True)

    with pytest.raises(KeyError):
        translator.t("nonexistent.key")


def test_plural_lookup_uses_one_form():
    translator = Translator(default_locale="en")

    assert translator.tn("notify.pending_validations", count=1) == (
        "There is 1 pending validation."
    )


def test_plural_lookup_uses_other_form():
    translator = Translator(default_locale="en")

    assert translator.tn("notify.pending_validations", count=3) == (
        "There are 3 pending validations."
    )
