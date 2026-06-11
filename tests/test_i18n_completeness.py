from citadel.i18n.translator import Translator


def _flatten(d, prefix=""):
    """Yield all dot-notation leaf keys from a nested dict."""
    for k, v in d.items():
        full = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            if "one" in v or "other" in v:
                yield full
            else:
                yield from _flatten(v, full)
        else:
            yield full


def test_catalog_key_sets_are_identical():
    t = Translator()
    en_keys = set(_flatten(t.catalogs["en"]))
    de_keys = set(_flatten(t.catalogs["de"]))
    missing_in_de = en_keys - de_keys
    missing_in_en = de_keys - en_keys

    assert not missing_in_de, f"Keys in en.yaml but not de.yaml: {missing_in_de}"
    assert not missing_in_en, f"Keys in de.yaml but not en.yaml: {missing_in_en}"


def test_plural_nodes_have_both_forms():
    t = Translator()

    for locale, catalog in t.catalogs.items():

        def check(d, path=""):
            for k, v in d.items():
                full = f"{path}.{k}" if path else k
                if isinstance(v, dict):
                    if "one" in v or "other" in v:
                        assert "one" in v, f"{locale}/{full} missing 'one'"
                        assert "other" in v, f"{locale}/{full} missing 'other'"
                    else:
                        check(v, full)

        check(catalog)
