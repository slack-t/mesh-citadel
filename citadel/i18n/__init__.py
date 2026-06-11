from citadel.i18n.translator import Translator

_translator = Translator(default_locale="de")
t = _translator.t
tn = _translator.tn


def resolve_locale(state, config) -> str:
    """Return the effective locale for a session.

    Priority: session override -> config system.locale -> hardcoded fallback "de".
    """
    if state and getattr(state, "locale", None):
        return state.locale
    if config and isinstance(getattr(config, "system", None), dict):
        return config.system.get("locale", "de")
    return "de"


def get_localized_config(value, locale: str, fallback: str = "") -> str:
    """Resolve a config value that is either a plain string or a locale map.

    Priority: exact locale match -> 'en' fallback -> fallback arg.
    """
    if isinstance(value, dict):
        return value.get(locale) or value.get("en") or fallback
    return value or fallback


__all__ = ["Translator", "get_localized_config", "resolve_locale", "t", "tn"]
