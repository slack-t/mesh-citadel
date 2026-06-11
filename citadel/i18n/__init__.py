from citadel.i18n.translator import Translator

_translator = Translator(default_locale="de")
t = _translator.t
tn = _translator.tn

__all__ = ["Translator", "t", "tn"]
