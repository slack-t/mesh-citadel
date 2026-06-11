# Internationalization (i18n) Plan

Status: draft, 2026-06-10 (rev: English is the canonical default). Goal: stop
hardcoding user-facing text (currently German literals scattered across the code)
and make the BBS translatable to any language. **English (`en`) is the canonical
default locale and the source of truth**; German (`de`) becomes the first
translation. To avoid churning the (currently German-asserting) test suite during
the move, `de` stays the *active* default while strings are migrated, and the
default is flipped to `en` in a dedicated final step (see §5).

---

## 1. Where the strings live today

User-facing text is inlined as literals, mostly inside `ToUser(text=...)`:

| Area | Files | Notes |
|------|-------|-------|
| Commands | `citadel/commands/builtins.py` | biggest source; `short_text`/`help_text` + every `ToUser` |
| Workflows | `citadel/workflows/*.py` | login, register_user, enter_message, create_room, validate_users, edit_user |
| Command routing | `citadel/commands/processor.py` | error packets |
| Input validation | `citadel/transport/validator.py` | error packets |
| MeshCore prompts | `citadel/transport/engines/meshcore/message_router.py` | prompts, **English/German mix**, pluralization |
| CLI formatting | `citadel/transport/engines/cli.py` | prompt strings |
| Permissions | `citadel/auth/permissions.py` | `permission_denied()` + action descriptions |
| System logs | `citadel/room/room.py`, `validate_users.py` | currently **English**, stored in System room |
| Config text | `config.yaml` | `welcome_message`, `registration.terms`, `room_names`, `recovery_questions` |
| CLI client | `cli_client.py` | separate process — its own German strings |

Two recurring complications the design must handle:

- **Named interpolation**: `f"Willkommen im Raum '{new_room.name}'."`,
  `f"Nachricht {msg_id} in {room.name} rausgehauen."`, etc. Translators must be
  able to reorder variables, so placeholders must be **named**, not positional.
- **Pluralization**, currently hand-coded in English:
  `message_router.py` ("There is/are N validation(s)"), `StopCommand`
  ("message"/"messages"). Needs first-class plural support.
- Several strings are **half-translated today** (e.g. `GoNextUnreadCommand`:
  `"Willkommen im Raum '...'. New messages are available in other rooms."`). The
  migration is the natural moment to fix these.

---

## 2. Approach — recommendation and the alternative

### Recommended: lightweight key-based YAML catalogs

A small in-house catalog system. Fits the project ethos (lightweight, runs on a
Pi Zero, readable, no binary build step) and matches the fact that some text
already lives in `config.yaml`.

- One file per locale: `citadel/i18n/catalogs/en.yaml` (canonical source of
  truth), `.../de.yaml` (translation).
- Nested keys map to strings with **named** `{placeholders}`.
- Plurals expressed as `one`/`other` subkeys, selected by a `count` argument.

```yaml
# en.yaml  (canonical source of truth)
room:
  welcome: "Welcome to the '{room}' room."
  posted: "Message {msg_id} posted in {room}."
errors:
  not_logged_in: "You need to log in first."
notify:
  pending_validations:
    one: "* There is {count} validation to review"
    other: "* There are {count} validations to review"
```

```yaml
# de.yaml  (translation; mirrors the same keys)
room:
  welcome: "Willkommen im Raum '{room}'."
  posted: "Nachricht {msg_id} in {room} rausgehauen."
errors:
  not_logged_in: "Du musst dich einloggen, Digger."
notify:
  pending_validations:
    one: "* Es gibt {count} Freigabe zu prüfen"
    other: "* Es gibt {count} Freigaben zu prüfen"
```

```python
t("room.welcome", room=new_room.name)
t("notify.pending_validations", count=n)   # picks one/other by n
```

### Alternative: Python stdlib `gettext`

The industry standard. `.po`/`.mo` files, `pybabel`/`xgettext` extraction,
`ngettext` plurals with correct CLDR plural rules, mature PO-editor tooling.

Prefer gettext if you expect **many** locales, professional translators, or
languages with complex plural rules (Polish, Arabic, Russian). Costs: a binary
`.mo` compile step, a less obvious workflow for casual contributors, and
positional/`%`-style or `{}`-style interpolation that is clunkier than named
keys for this codebase.

> For a single-maintainer German fork that mainly wants "de + maybe en/a few
> more", the YAML approach is lower friction. The rest of this plan assumes it,
> but every phase maps cleanly onto gettext if you choose it instead.

---

## 3. Core module design (`citadel/i18n/`)

```
citadel/i18n/
  __init__.py        # exposes `i18n` singleton + `t(...)`
  translator.py      # Translator class
  catalogs/
    de.yaml          # default — seeded with TODAY'S German strings
    en.yaml          # added in a later phase
```

```python
class Translator:
    def __init__(self, default_locale="en", available=("en", "de")):  # config sets de during migration
        self.default = default_locale
        self.catalogs = { loc: _load_yaml(loc) for loc in available }

    def translate(self, key, *, locale=None, count=None, **kwargs):
        loc = locale or self.default
        entry = self._lookup(loc, key) or self._lookup(self.default, key)
        if entry is None:
            log.warning("Missing i18n key: %s (%s)", key, loc)
            return key                       # fail-soft, never crash a response
        if isinstance(entry, dict):          # plural form
            entry = entry["one" if count == 1 else "other"]
        try:
            return entry.format(count=count, **kwargs)
        except KeyError as e:
            log.error("i18n %s missing placeholder %s", key, e)
            return entry
```

Design rules:
- **Fail-soft**: a missing key or placeholder returns something printable and
  logs — a translation gap must never break a user's session.
- **Fallback chain**: requested locale → default locale → the key itself.
- Locale + available locales come from config (`system.locale`,
  `system.available_locales`); initialized once in `initialize_system()`
  (`main.py`) alongside the other singletons.

---

## 4. Threading the locale through requests

Most call sites already carry a `context` (`CommandContext` /
`WorkflowContext`) that has `config`, `session_mgr`, and `session_id` — enough to
resolve a locale. Plan:

1. Add `locale: Optional[str]` to `SessionState` (`session/state.py`), defaulting
   to `None` (→ server default).
2. Add a tiny resolver: `resolve_locale(session_state, config) -> str`.
3. Give `CommandContext`/`WorkflowContext` a bound helper so call sites stay
   terse:
   ```python
   context.t("room.welcome", room=name)   # locale resolved from the session
   ```
   Implement as a method that calls `i18n.translate(key, locale=self._locale, ...)`.
4. The few helpers that take only `session_id`/`user` (notably
   `permissions.permission_denied(...)`) get a `locale` parameter (or resolve via
   the passed `user` once per-user language exists — see Phase 6).

Pre-login prompts (login/registration) run before any user language is known, so
they use the **server default** locale. That's acceptable; per-user language is
selected *during* registration (Phase 6).

---

## 5. Phased rollout

### Phase 0 — decisions
Pick YAML-catalog vs gettext (§2); lock the key-naming convention
(`area.subarea.name`, lower_snake); decide server-wide-only vs per-user language
(recommend: ship server-wide first, per-user in Phase 6).

### Phase 1 — core, behavior-preserving
Build `citadel/i18n/` (§3). Seed `de.yaml` with the **exact** current German
strings, and author `en.yaml` (canonical English) for each key as you go. Wire
the singleton in `main.py`, but **keep the active default = `de` for now** (via
config). No call sites changed yet.
**Property: output is byte-identical, so the existing test suite stays green.**

### Phase 2 — plumb the locale
Add `SessionState.locale`, the resolver, and `context.t(...)` (§4). Still no
strings moved.

### Phase 3 — mechanical migration, module by module
Replace literals with `t("key", ...)`, one module per change for reviewability.
Suggested order (ascending risk/volume):
`validator.py` → `processor.py` → `permissions.py` → each `workflows/*.py` →
`builtins.py` (largest) → `message_router.py` / `cli.py`. Fix the half-translated
strings as you go. Because `de` is the default catalog, tests that assert German
substrings keep passing.

### Phase 4 — config-embedded text
Move `welcome_message`, `registration.terms`, `room_names` defaults, and
`recovery_questions` out of a single hardcoded language. Options: keep them in
`config.yaml` but as per-locale maps, or move them into the catalogs. `terms` is
legal text and should be translatable per locale. Decide whether System-room log
lines (`Room.system_log`, validation logs) are localized to the server default or
pinned to one operator language (recommend: server default).

### Phase 5 — complete English, flip the default, add guards
By now `en.yaml` (canonical) and `de.yaml` both exist. Verify `en.yaml` is
complete, then **flip the active default locale to `en`** (`system.locale: en`).
This is the point where day-one output changes from German to English, so update
tests: legacy assertions that check German text either move to English, or pin
their test session to `locale: de` (keep a handful of the latter to exercise the
translation path). Add completeness guards to CI / `pytest`:
- catalog completeness: key sets of all locales are identical;
- every `t()` key used in code exists in the catalogs (scan for `t("...")` /
  `context.t("...")`);
- plural entries have both `one` and `other`.

### Phase 6 — optional / later
- **Per-user language**: add a nullable `language` column to `users`; pick it
  during registration; cache on `SessionState` at login; resolver prefers it over
  config. Requires a tiny schema migration in `db/initializer.py`.
- **CLI client** (`cli_client.py`): separate process — give it the same catalogs
  (import `citadel.i18n` or ship a copy) so `/hilfe` etc. are translatable.
- **Locale-aware dates/numbers**: today `format_timestamp` uses a config
  `date_format` + timezone. If desired, switch to Babel for locale-correct dates;
  otherwise keep per-locale `date_format` strings in the catalogs.

---

## 6. Testing strategy

- **Translator unit tests**: lookup, locale fallback, default fallback,
  missing-key → key returned + warning, plural selection, named interpolation,
  missing-placeholder fail-soft.
- **Regression safety**: Phases 1–4 keep `de` as the active default so existing
  German assertions stay valid; no test churn during the big sweep. The Phase 5
  default-flip to `en` is the single, deliberate point where assertions update.
- **Completeness guards** (Phase 5) as above — these catch the main failure mode
  of any i18n effort: catalogs drifting out of sync.
- Optional heuristic test/lint: flag new non-ASCII string literals inside
  `ToUser(...)` to discourage regressions back to hardcoded text.

---

## 7. Effort & risk

- Phases 1–2: small, isolated, low risk.
- Phase 3: large but mechanical and incremental; main risk is *missing* a string
  or breaking an f-string's variables — mitigated by going module-by-module and
  the completeness guards.
- Phases 4–6: independent, can be scheduled later.

Coordinate with `docs/KNOWN_ISSUES_FIX_PLAN.md`: the duplicate-command-code fix
touches `short_text`/`help_text` on the same command classes this plan will
re-key — do that fix **first** so strings are only moved once.
