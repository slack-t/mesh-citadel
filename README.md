# mesh-citadel-ng

A BBS (Bulletin Board System) for [MeshCore](https://github.com/ripplebiz/MeshCore), inspired by the Citadel BBS of the 1980s. Designed to run on a solar-powered Raspberry Pi Zero connected to an nRF52-based LoRa node via the MeshCore USB Companion firmware.

> **This is a fork.** Full credit and thanks to [taedryn](https://github.com/taedryn) for creating the original [mesh-citadel](https://github.com/taedryn/mesh-citadel). This project builds directly on that foundation. The original copyright and [Forklift Certified License](LICENSE) are retained; the project was renamed per the license to make clear this is an independent continuation.

**Alpha software.** It will probably crash. Have fun anyway.

---

## What's different from the original

### 1. Internationalization (i18n)
The original has all user-facing strings hardcoded in German. mesh-citadel-ng introduces a full i18n system:

- A YAML-based translation catalog (`citadel/i18n/catalogs/`) with English (`en.yaml`) and German (`de.yaml`) translations for every user-facing string.
- A `Translator` singleton with locale resolution: session locale → config `system.locale` → server default.
- `context.t("key")` call sites throughout commands, workflows, permissions, and system messages — no more hardcoded strings in code.
- **English is the server default.** German is a fully supported locale, selectable via `system.locale: de` in `config.yaml`.
- A CI completeness guard that fails if any `t()` key used in code is missing from the English catalog.

### 2. Rehabilitated test suite
The original test suite had 53 failing tests (out of ~130) due to API drift. mesh-citadel-ng:

- Fixed all failing tests to match the current codebase API.
- Added new tests for i18n infrastructure, locale resolution, and catalog completeness.
- Grows the suite to **159 passing tests, 0 failing**.

### 3. CI pipeline
Added a GitHub Actions workflow that runs the full pytest suite on every push and pull request.

### 4. Bug fixes
- Fixed a `Room` deletion bug that could corrupt room state.
- Fixed a broken category filter in `HelpCommand._build_category_menu`.
- Fixed help category headers rendering mixed-language output (e.g. "Common Kommandos:" in English mode).
- Removed a duplicate `from citadel.i18n import t` inside `get_system_room_names` that shadowed the module-level import.
- Various session management and async cleanup fixes.

---

## Features (inherited from original)

- User registration and login
- Room navigation and message reading/posting
- Private mail (DM via Mail room)
- Permission levels: Twit, User, Aide, Sysop
- MeshCore transport (USB Companion Radio)
- CLI client for local admin access
- In-memory SQLite mode for fast operation on SD-card hardware
- Configurable limits (rooms, messages, users) via `config.yaml`

---

## Quick start

```bash
pip install -r requirements.txt
# Edit config.yaml — set system.locale, bbs name, etc.
python main.py
```

First login becomes Sysop. Use `cli_client.py` to do this locally before exposing the BBS over MeshCore.

> Set `database.use_memory: false` during initial setup, then flip it to `true` once everything works — the in-memory mode is significantly faster on Pi hardware.

---

## User commands

| Key | Command |
|-----|---------|
| `N` | Read new messages |
| `S` | Post a message (or send mail in the Mail room) |
| `W` | Go to next room with unread messages |
| `H` | Help — list all commands; `H <cmd>` for details |
| `R` | List rooms (`*` = unread, `-` = nothing new) |
| `G` | Go to room by name or ID |
| `O` | Who's online |
| `.N` | Create a new room (Aide+) |

---

## Language configuration

The server default is English. To run in German, add to `config.yaml`:

```yaml
system:
  locale: de
```

Per-session locale override is also supported via `SessionState.locale` for future per-user language assignment.

---

## Contributing

Still early. If you find a bug, open an issue — describe who you were, which room you were in, and what you broke.
