# Willkommen in der MeshcoreBayreuth BBS!

Old-School-Text-Chat über ein modernes Mesh-Netzwerk. Keine bunten Bilder – nur Räume, Nachrichten und Leute. Hier ist alles, was du zum Loslegen brauchst.

---

## 1. Verbinden

Der Node schickt alle 12 Stunden einen **Flood Advert** (Region: de-by-fr) unter dem Namen **"MeshcoreBayreuth BBS"**. Schick ihm einfach eine Direktnachricht und du bist drin.

Die Begrüßung sieht so aus:

> **Wer bist du? (Username):**

Wenn du schon einen Account hast, tipp einfach deinen Usernamen ein. Wenn nicht, tipp **`new`** um dich zu registrieren.

---

## 2. Registrierung

Wenn du `new` eingibst, führt dich das System durch fünf Schritte:

1. **Username** — dein Login-Name (nur Buchstaben und Zahlen, mindestens 3 Zeichen)
2. **Anzeigename** — was andere sehen, wenn du postest
3. **Passwort** — mindestens 6 Zeichen
4. **Regeln** — lies die Bedingungen und tippe `ja` zum Akzeptieren (oder `nein` zum Abbrechen)
5. **Motto** — eine kurze Vorstellung von dir

> Neue Accounts müssen erst von einem Sysop freigeschaltet werden, bevor du überall schreiben kannst. Hab etwas Geduld!

---

## 3. Räume

Die BBS ist in Räume unterteilt, jeder mit seinem eigenen Thema. Nach dem Login landest du in der **Lobby**.

| Kommando | Was es macht |
|----------|-------------|
| `K` | Alle Räume anzeigen, auf die du Zugriff hast |
| `G` | In einen Raum wechseln – `G` tippen, dann Raumname oder ID eingeben |
| `W` | Zum nächsten Raum mit ungelesenen Nachrichten springen |
| `I` | Raum ignorieren (blendet ihn aus deiner Ansicht aus) |

---

## 4. Nachrichten lesen

| Kommando | Was es macht |
|----------|-------------|
| `N` | Neue Nachrichten lesen (nur was du noch nicht gesehen hast) |
| `R` | Alle Nachrichten lesen, neueste zuerst |
| `V` | Alle Nachrichten lesen, älteste zuerst |
| `U` | Nachrichten überfliegen – kurze Übersicht |
| `STOPP` | Wiedergabe stoppen, wenn die Nachrichtenliste lang ist |

---

## 5. Nachricht schreiben

1. Tippe **`S`** um eine Nachricht im aktuellen Raum zu verfassen.
2. Schreib deinen Text – mehrere Zeilen sind kein Problem.
3. Zum Abschicken: neue Zeile anfangen, einen einzelnen Punkt (`.`) tippen und Enter drücken.

---

## 6. Private Nachrichten (Mail)

So schickst du jemandem eine private Nachricht:

1. Tippe **`M`** um direkt in den Mail-Raum zu springen.
2. Tippe **`S`** um eine Nachricht zu schreiben. Das System fragt dann nach dem Usernamen des Empfängers.

---

## 7. Alle Kommandos

### Für alle

| Kommando | Was es macht |
|----------|-------------|
| `N` | Neue Nachrichten lesen |
| `S` | Nachricht schreiben |
| `R` | Alle Nachrichten lesen (neueste zuerst) |
| `V` | Alle Nachrichten lesen (älteste zuerst) |
| `U` | Nachrichten überfliegen |
| `K` | Bekannte Räume anzeigen |
| `G` | Raum wechseln |
| `W` | Nächster Raum mit ungelesenen Nachrichten |
| `M` | In den Mail-Raum wechseln |
| `O` | Wer ist online? |
| `H` | Hilfe – alle Kommandos anzeigen; `H <Kommando>` für Details |
| `?` | Wie `H` |
| `I` | Aktuellen Raum ignorieren |
| `T` | Ausloggen |
| `STOPP` | Nachrichten-Wiedergabe stoppen |
| `ABBRUCH` | Aktuelle Aktion abbrechen (z.B. beim Schreiben oder mitten in einem Workflow) |

### Aides und Sysops

| Kommando | Was es macht |
|----------|-------------|
| `.N` | Neuen Raum erstellen |
| `P` | Neue Accounts prüfen (freischalten oder ablehnen) |
| `B` | Benutzer blockieren |
| `L` | Nachricht löschen |
| `.RR` | Raumeinstellungen bearbeiten |
| `.UB` | Benutzer-Account bearbeiten |
| `.KR` | Raum löschen |

---

## 8. Tipps

- Wenn du dich in einem Workflow verlaufen hast (z.B. beim Schreiben einer Nachricht), tippe **`ABBRUCH`** und drücke Enter.
- `H S` zeigt dir ausführliche Hilfe zum `S`-Kommando. Das funktioniert für jedes Kommando.
- Der erste User, der sich einloggt, wird automatisch Sysop.

---

## Credits

Diese BBS läuft auf **mesh-citadel-ng**, einem Fork von [taedryns mesh-citadel](https://github.com/taedryn/mesh-citadel) – einem MeshCore-Port des klassischen Citadel-BBS-Konzepts aus den 1980ern.
