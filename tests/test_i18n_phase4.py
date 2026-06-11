from citadel.i18n import get_localized_config, t


def test_get_localized_config_plain_string_returned_as_is():
    assert get_localized_config("Hello!", "de") == "Hello!"
    assert get_localized_config("Hello!", "en") == "Hello!"


def test_get_localized_config_locale_map_exact_match():
    val = {"en": "Hello!", "de": "Hallo!"}

    assert get_localized_config(val, "de") == "Hallo!"
    assert get_localized_config(val, "en") == "Hello!"


def test_get_localized_config_locale_map_falls_back_to_en():
    val = {"en": "Hello!"}

    assert get_localized_config(val, "de") == "Hello!"


def test_get_localized_config_locale_map_uses_fallback_arg():
    val = {"fr": "Bonjour!"}

    assert get_localized_config(val, "de", fallback="???") == "???"


def test_get_localized_config_none_uses_fallback_arg():
    assert get_localized_config(None, "de", fallback="default") == "default"


def test_system_log_keys_exist_in_both_locales():
    keys = [
        "system_log.room_created",
        "system_log.room_deleted",
        "system_log.user_validated",
        "system_log.user_rejected",
        "system_log.user_registered",
    ]
    for key in keys:
        en = t(
            key,
            locale="en",
            name="X",
            creator="Y",
            validator="Z",
            username="U",
            display_name="D",
        )
        de = t(
            key,
            locale="de",
            name="X",
            creator="Y",
            validator="Z",
            username="U",
            display_name="D",
        )

        assert en != key, f"Missing en.yaml key: {key}"
        assert de != key, f"Missing de.yaml key: {key}"


def test_bbs_room_name_keys_exist():
    for slug in ("lobby", "mail", "aides", "sysop", "system", "twit"):
        key = f"bbs.room_names.{slug}"

        assert t(key, locale="en") != key
        assert t(key, locale="de") != key


def test_bbs_welcome_default_has_name_placeholder():
    result = t("bbs.welcome_default", locale="de", name="TestBBS")

    assert "TestBBS" in result
