# Welcome to MeshcoreBayreuth BBS!

Old-school text chat over a modern mesh network. No flashy images — just rooms, messages, and people. Here's everything you need to get started.

---

## 1. Connecting

The node broadcasts a **Flood Advert** (region scope: de-by-fr) every 12 hours under the name **"MeshcoreBayreuth BBS"**. Send it a direct message and you'll be connected.

You'll be greeted with:

> **Who are you? (Username):**

If you already have an account, type your username. If not, type **`new`** to register.

---

## 2. Registration

When you type `new`, the system walks you through five steps:

1. **Username** — your login name (letters and numbers only, at least 3 characters)
2. **Display name** — what others see when you post
3. **Password** — at least 6 characters
4. **Terms** — read the rules and type `yes` to accept (or `no` to bail)
5. **Motto** — a short intro about yourself

> New accounts need to be approved by a Sysop before you can post everywhere. Sit tight after registering.

---

## 3. Rooms

The BBS is divided into rooms, each with its own topic. After login you land in the **Lobby**.

| Command | What it does |
|---------|-------------|
| `K` | List all rooms you have access to |
| `G` | Go to a room — type `G`, then the room name or ID |
| `W` | Jump to the next room that has unread messages |
| `I` | Ignore a room (hides it from your view) |

---

## 4. Reading messages

| Command | What it does |
|---------|-------------|
| `N` | Read new messages (only what you haven't seen yet) |
| `R` | Read all messages, newest first |
| `V` | Read all messages, oldest first |
| `U` | Scan messages — short summary view |
| `STOPP` | Stop mid-playback if the message list is long |

---

## 5. Writing a message

1. Type **`S`** to compose a message in the current room.
2. Write your text — multiple lines are fine.
3. To send: start a new line, type a single period (`.`), and press Enter.

---

## 6. Private mail

To send a private message to another user:

1. Type **`M`** to jump straight to the Mail room.
2. Type **`S`** to write a message. The system will ask for the recipient's username.

---

## 7. All commands

### Everyone

| Command | What it does |
|---------|-------------|
| `N` | Read new messages |
| `S` | Write a message |
| `R` | Read all messages (newest first) |
| `V` | Read all messages (oldest first) |
| `U` | Scan messages |
| `K` | List known rooms |
| `G` | Go to room |
| `W` | Next room with unread messages |
| `M` | Go to Mail room |
| `O` | Who's online |
| `H` | Help — list all commands; `H <cmd>` for details |
| `?` | Same as `H` |
| `I` | Ignore current room |
| `T` | Quit (log out cleanly) |
| `STOPP` | Stop message playback |
| `ABBRUCH` | Cancel the current action (e.g. mid-message, mid-workflow) |

### Aides and Sysops

| Command | What it does |
|---------|-------------|
| `.N` | Create a new room |
| `P` | Validate (approve/reject) pending user accounts |
| `B` | Block a user |
| `L` | Delete a message |
| `.RR` | Edit room settings |
| `.UB` | Edit a user account |
| `.KR` | Delete a room |

---

## 8. Tips

- If you get lost in a workflow (e.g. you started writing a message and want out), type **`ABBRUCH`** and press Enter.
- `H W` shows you detailed help for the `W` command. This works for any command.
- The first user to log in becomes Sysop.

---

## Credits

This BBS runs **mesh-citadel-ng**, a fork of [taedryn's mesh-citadel](https://github.com/taedryn/mesh-citadel), which is a MeshCore port of the classic Citadel BBS concept from the 1980s.
