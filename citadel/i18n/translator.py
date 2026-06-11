import logging
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)


class Translator:
    def __init__(
        self,
        default_locale: str = "de",
        available: tuple[str, ...] = ("en", "de"),
        strict: bool = False,
    ):
        self.default_locale = default_locale
        self.available = available
        self.strict = strict
        self.catalogs = self._load_catalogs()

    def t(self, key: str, locale: str | None = None, **kwargs) -> str:
        """Look up key, interpolate kwargs, return string."""
        value = self._lookup(key, locale)
        if not isinstance(value, str):
            return self._missing(key, locale)
        return self._format(key, value, kwargs)

    def tn(
        self,
        key: str,
        count: int,
        locale: str | None = None,
        **kwargs,
    ) -> str:
        """Plural-aware lookup using 'one' for count==1 and 'other' otherwise."""
        plural_key = "one" if count == 1 else "other"
        value = self._lookup(f"{key}.{plural_key}", locale)
        if not isinstance(value, str):
            return self._missing(key, locale)
        return self._format(key, value, {"count": count, **kwargs})

    def _load_catalogs(self) -> dict[str, dict[str, Any]]:
        catalogs_dir = Path(__file__).with_name("catalogs")
        catalogs = {}
        for locale in self.available:
            catalog_path = catalogs_dir / f"{locale}.yaml"
            with catalog_path.open(encoding="utf-8") as catalog_file:
                catalogs[locale] = yaml.safe_load(catalog_file) or {}
        return catalogs

    def _lookup(self, key: str, locale: str | None) -> Any:
        selected_locale = locale or self.default_locale
        catalog = self.catalogs.get(selected_locale)
        if catalog is None:
            return None

        value: Any = catalog
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return None
            value = value[part]
        return value

    def _missing(self, key: str, locale: str | None) -> str:
        selected_locale = locale or self.default_locale
        message = f"Missing i18n key {key!r} for locale {selected_locale!r}"
        if self.strict:
            raise KeyError(message)
        log.warning(message)
        return key

    def _format(self, key: str, template: str, kwargs: dict[str, Any]) -> str:
        try:
            return template.format_map(kwargs)
        except KeyError as exc:
            message = f"Missing placeholder {exc.args[0]!r} for i18n key {key!r}"
            if self.strict:
                raise KeyError(message) from exc
            log.warning(message)
            return key
