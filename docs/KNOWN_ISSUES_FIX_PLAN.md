# Known Issues — Implementation / Fix Plan

Status: draft, 2026-06-10. Scope: bugs and incomplete features found during a
full codebase review. Each item lists the root cause (with `file:line`), the
user-visible impact, and a proposed fix. Items are ordered by severity.

> Note: at the time of writing, `.pytest_cache` shows most of the suite failing
> on its last run, including `test_room_object.py`, `test_command_handlers.py`,
> and `test_command_processor.py`. Several issues below are the likely cause and
> have existing tests that should go green once fixed.

---

## P0 — Duplicate command codes (silent shadowing)

### Symptom
Three command codes are registered twice. `CommandRegistry.register()`
(`citadel/commands/registry.py:11`) does `self._commands[code] = cls`, so the
**last** class registered for a code wins and the earlier one becomes
unreachable from the text parser and the help menu.

| Code | First (shadowed)            | Second (wins)                 |
|------|-----------------------------|-------------------------------|
| `O`  | `GoNextUnreadCommand` (109) | `WhoCommand` (628)            |
| `U`  | `EnterMessageCommand` (153) | `ScanMessagesCommand` (414)   |
| `P`  | `ForwardReadCommand` (214)  | `ValidateUsersCommand` (775)  |

All line numbers in `citadel/commands/builtins.py`.

### Impact
- **`enter_message` is unreachable** — there is currently no working top-level
  command to *write* a message (the `U` slot resolves to `scan_messages`). This
  is the most user-impactful bug in the project.
- `go_next_unread` ("next room with unread") is unreachable (`O` → `who`).
- `forward_read` is unreachable (`P` → `validate_users`).

### Proposed fix
1. **Assign unique codes.** Final letters are the maintainer's call (this is a
   German fork — German mnemonics may be preferred). One workable, collision-free
   mapping that keeps the most-used commands on memorable keys:

   | name             | current | proposed | rationale                          |
   |------------------|---------|----------|------------------------------------|
   | `enter_message`  | `U`     | `S`      | "Schreiben" — and frees `U`        |
   | `scan_messages`  | `U`     | `U`      | keep                               |
   | `go_next_unread` | `O`     | `W`      | "Weiter" (README already uses W)   |
   | `who`            | `O`     | `O`      | keep ("Online")                    |
   | `forward_read`   | `P`     | `V`      | "Vorwärts"                         |
   | `validate_users` | `P`     | `P`      | keep                               |

   Update each class's `code`, plus any `short_text`/`help_text` that names the
   key, and the README command list to match.

2. **Add a hard guard so this can never silently happen again.** In
   `CommandRegistry.register()`:

   ```python
   if command_cls.code in self._commands:
       existing = self._commands[command_cls.code]
       raise ValueError(
           f"Command code {command_cls.code!r} already registered to "
           f"{existing.__name__}; cannot also register {command_cls.__name__}")
   ```

   With the guard in place, importing `builtins.py` will fail loudly at startup
   until the codes are made unique — which is what we want.

### Tests
- Add a registry test asserting no two registered classes share a `code`.
- `test_command_handlers.py` / `test_help_command.py` should be re-checked once
  codes change (they may assert specific letters).

---

## P0 — `Room.delete_room()` raises `NameError`

### Root cause
`citadel/room/room.py:514`:

```python
await Room.initialize_room_order(db, config)   # db, config are undefined here
```

The method has `self`, not `db`/`config` in scope.

### Impact
Any room deletion (`.KR` `KillRoomCommand`, `builtins.py:919`) crashes after the
row is already deleted, leaving the room chain in an inconsistent state. The test
`test_room_deletion_logs_event` (`test_room_object.py:193`) fails.

### Proposed fix
```python
await Room.initialize_room_order(self.db, self.config)
```

While here, also finish the two TODOs on lines 515–516, which are real
correctness gaps:
- **Relink neighbors** before deleting so the doubly-linked list stays intact:
  set the previous room's `next_neighbor` to this room's `next_neighbor` and the
  next room's `prev_neighbor` to this room's `prev_neighbor`. (Today the chain is
  only repaired opportunistically by `initialize_room_order`'s orphan recovery.)
- **Remove linked messages**: delete rows from `room_messages` (and orphaned
  `messages`) for the deleted room. The schema declares
  `ON DELETE CASCADE`, but SQLite only enforces foreign keys when
  `PRAGMA foreign_keys = ON` is set — verify that pragma is enabled in
  `DatabaseManager`; if not, delete explicitly.

Message-string nit: the system log writes `"...was deleted"` (no period) but
`test_room_object.py:210` asserts the substring `"...was deleted."` (with
period). Align the two — add the period (and optionally translate this
System-room log line; it is currently English).

---

## P1 — `Room.get_next_unread_message()` missing `await`

### Root cause
`citadel/room/room.py:359`:

```python
last_seen = self.get_last_unread_message_id(user)   # returns a coroutine, not an int
```

`get_last_unread_message_id` is `async`. Without `await`, `last_seen` is a
truthy coroutine object, so the "first visit" branch (`if not last_seen`) never
runs and `message_ids.index(last_seen)` raises `ValueError`, which is swallowed
and returns `None`.

### Impact
The method effectively always returns `None`. `test_user_read_tracking`
(`test_room_object.py:164`) fails. (Production command paths currently use
`get_unread_message_ids`, so end-user impact is limited today, but the function
is part of the public Room API and is tested.)

### Proposed fix
```python
last_seen = await self.get_last_unread_message_id(user)
```

Related cleanup in `get_last_unread_message_id` (`room.py:185`): it accepts
`User | str` and computes `username`, but the query then hard-codes
`user.username`, so passing a `str` raises `AttributeError`. Use the resolved
`username` variable in the query.

---

## P1 — `ContactManager` DB helpers broken

File: `citadel/transport/engines/meshcore/contacts.py`.

### a) `_sync_node_to_db()` never calls the coroutine — line 358
```python
contacts = self._get_all_node_contacts      # missing await + ()
for node_id, contact in contacts.items():   # AttributeError: coroutine has no .items()
```
Fix:
```python
contacts = await self._get_all_node_contacts()
```
Impact: first-run "node → database" contact sync (a newly installed BBS whose
node already has contacts) crashes. Reachable via `synchronize()` when
`contact_manager.update_contacts: true`.

### b) `_delete_contact_from_db()` — line 546
Two bugs:
```python
await self.db.execute(query, contact.node_id)   # str, not a params tuple
...
del self._db_cache[node_id]                     # node_id is undefined here
```
Fix:
```python
await self.db.execute(query, (contact.node_id,))
...
self._db_cache.pop(contact.node_id, None)
```
Impact: deleting a contact crashes (and would `KeyError`/`NameError` even if the
query succeeded). Reachable via `ContactManager.delete_contact()`.

### Tests
There is currently little/no coverage for `ContactManager`. Add focused unit
tests with a fake `meshcore` and the in-memory DB for `add_contact`,
`delete_contact`, and both sync directions.

---

## P2 — `edit_user` workflow is non-functional (rewrite)

File: `citadel/workflows/edit_user.py`. The whole module targets an old API that
no longer exists and will crash immediately if ever entered:

- `user = user.User(session.username)` (line 18) — wrong constructor, shadows the
  `user` module/var. Should be `User(context.db, session.username)` + `await load()`.
- `db.get_user(...)` / `db.update_user(...)` — these methods do not exist on
  `DatabaseManager`. Use `User` instances: `User(db, name)`, `await u.load()`,
  and the existing setters (`set_display_name`, `set_permission_level`,
  `set_status`).
- Uses `.permission` throughout; the attribute is `.permission_level`.
- Step-4 menu build: `for i, level in levels` (line 112) iterates a list of
  enums, not `enumerate(...)` — `ValueError`.
- Step-4 handler: `new_perm = list(PermissionLevel)[index]` (line 139) ignores
  the aide-cannot-grant-sysop restriction applied when the menu was *shown*, so
  an aide could escalate by index. Re-apply the filter when validating.

Additionally, the command that should launch it, `EditUserCommand` (`.UB`,
`builtins.py:880`), has **no `run()` method**, so `is_implemented()` is `False`
and the workflow is currently unreachable anyway.

### Proposed fix
Rewrite the workflow against the current `User`/`Room` APIs (mirror the shape of
`validate_users.py`, which is the closest correct example), then add a `run()` to
`EditUserCommand` that registers the workflow and calls `handler.start()` —
exactly like `CreateRoomCommand` (`builtins.py:838`) or `ValidateUsersCommand`
(`builtins.py:782`) already do. All new user-facing strings in German.

### Effort
This is the largest item — treat it as its own change, separate from the P0/P1
one-line fixes.

---

## P3 — Declared-but-unimplemented command stubs

These classes are registered but have no `run()` (so `is_implemented()` is
`False` and they're hidden from the help menu, but they still occupy a `code`):

- `IgnoreRoomCommand` `I` (`builtins.py:298`)
- `BlockUserCommand` `B` (765)
- `EditRoomCommand` `.RR` (870)
- `EditUserCommand` `.UB` (880) — see P2
- `FastForwardCommand` `.S` (889)

Not bugs, but worth tracking. `ignore_room` and `fast_forward` already have
supporting Room methods (`ignore_for_user` / `skip_to_latest`) and are cheap to
finish; `block_user` has `User.block_user`/`is_blocked` support. Decide per
feature whether to implement or remove the stub.

---

## Suggested sequencing

1. **Batch 1 (one-liners, unblock the test suite):** P0 `delete_room`, P1
   `get_next_unread_message` + `get_last_unread_message_id`, P1 contacts a/b.
   Small, isolated, each has or gains a test.
2. **Batch 2 (command codes):** add the registry collision guard *first* (it will
   make the suite fail fast at import), then assign unique codes and update README
   + any letter-specific tests. Verify `enter_message` is reachable end-to-end.
3. **Batch 3 (edit_user rewrite):** standalone, German strings, with new tests.
4. **Batch 4 (optional):** finish or remove the P3 stubs.

Run `pytest` after each batch; the `lastfailed` set is the fastest signal.
