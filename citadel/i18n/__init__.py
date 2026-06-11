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


__all__ = ["Translator", "resolve_locale", "t", "tn"]
