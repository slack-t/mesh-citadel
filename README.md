# Mesh-Citadel BBS (Die deutsche Slack-T Edition!)

**🚨 WICHTIG: Das hier ist ein Fork! 🚨**
Dies ist der extrem aufgemotzte und eingedeutschte Fork von [taedryn/mesh-citadel](https://github.com/taedryn/mesh-citadel). Alles hier wurde frisch übersetzt und mit einer ordentlichen Prise Humor verfeinert.

Dieses Projekt baut ein BBS (Bulletin Board System) für MeshCore, das stark an das gute alte Citadel BBS aus den 80ern erinnert. Das Ding ist extrem leichtgewichtig und dafür gedacht, auf einem solarbetriebenen Raspberry Pi Zero und einem energiesparenden nRF52-basierten LoRa-Node zu laufen (mit der USB Companion Firmware via py-meshcore).

# Was geht ab? (In Progress)

Letztes Update: Mon Nov  3 10:38:50 PST 2025 (Original)

**Das ist feinstes ALPHA-Zeug!** Es wird dir wahrscheinlich um die Ohren fliegen, wenn du es nur schief anschaust. 

Ich bin an dem Punkt, wo das Ding *fast* ein funktionierendes BBS ist. Was schon läuft:
* User-Registrierung
* Einloggen
* Zwischen den Räumen rumstolpern
* Nachrichten lesen
* Seinen Senf dazugeben (Nachrichten schreiben)
* Ab zur Post (Private Nachrichten verschicken)
* Berechtigungs-Kram
* MeshCore-Kommunikation

Es gibt *auf jeden Fall* noch Bugs und fehlende Features – sowohl in der BBS-Logik als auch in der MeshCore-Integration.

# Wie man Citadel benutzt (Als User)

1. Advert (Zeig dich!)
2. Schick was via DM
3. Einloggen, oder registrieren, indem du 'new' als Benutzernamen eingibst.
4. Warten, bis der Sysop dich für cool genug befindet und freischaltet.
5. Wieder einloggen.
6. Austoben!

Wenn du die Registrierung überlebt hast, muss dich ein Sysop oder Aide checken. Da es hier momentan nicht viele Türsteher gibt, hab Geduld!

Bist du drin, landest du direkt in der Lobby. Folgende Befehle könnten dir das Leben erleichtern (einfach den Buchstaben in die Tasten hauen):

### (N)eues lesen
Gibt dir den heißen Scheiß (Nachrichten, die du noch nicht gesehen hast). Momentan kommt das als fette Textwand, aber irgendwann vielleicht mal in mundgerechten Häppchen.

### (S)chreiben
Hau in die Tasten und poste eine Nachricht im aktuellen Raum. Schreib so viel du willst und beende dein Geschwafel mit einem simplen `.` (Punkt) in einer eigenen Zeile.
Bist du im Postamt (Mail Raum), musst du noch den Namen des Opfers angeben, dem du schreiben willst.

### (W)eiter zum nächsten (ungelesenen) Raum
Hüpfe in den nächsten Raum, wo noch was Neues steht. Gibt's nix mehr, bleibst du in der Lobby hocken. 

### (H)ilfe
Zeig mir die verdammte Anleitung! Eine Liste aller verfügbaren Befehle. Tipp: Gib "H W" ein, um mehr über das Weiter-Kommando zu lernen.

### (R)äume zeigen (Kennt man)
Zeig mir alle Räume, die es hier gibt. Ein Minus (-) davor heißt "Nix Neues, Digger". Ein Stern (*) heißt "Hier geht's ab, du hast ungelesene Nachrichten!". Nutze (W), um direkt hinzuspringen.

### (G)ehe zu Raum
Beam mich in einen anderen Raum! Gib den Namen oder die ID des Raums nach dem Befehl ein (z.B. "G Lobby" oder "G mail"). So kommst du ins Postamt, um private Nachrichten zu flüstern.

### (O)nline (Wer is da?)
Wer treibt sich gerade rum? Das System versucht, ein bisschen Datenschutz zu spielen: Nur wer in den letzten 2 Wochen gepostet hat, wird hier gelistet. Sysops und Aides sehen aber eh jeden. Big Brother is watching you!

### (.N)euer Raum
Achtung, mit Punkt davor! Zimmer mir einen neuen Raum. Startet einen schicken interaktiven Workflow.

# Du willst mitbasteln? (Contributions)

Ich bin noch nicht bereit für fremden Code. Ich hab noch ne Tonne an halbfertigen Ideen. Sobald das Ding nicht mehr beim Atmen abstürzt, schau ich mir Pull Requests an.

Wenn du Bugs findest: Schreib ein verdammtes Issue in dieses Repo! Sag mir, wer du bist, in welchem Raum du warst und was du kaputtgemacht hast. 

# Design-Philosophie

Das Ding ist absichtlich mega retro. Es fühlt sich genau wie Citadel aus den 80ern an. Für Neulinge ist das einfach nur "WTF ist dieses Interface?". Für alte Hasen ist es ein Nostalgie-Trip.

Teil des Retros-Charmes: Kein verdammtes Internet! Nur über's Mesh erreichbar. So bleiben die Gespräche schön lokal, genau wie in den guten alten Zeiten.

# Einen Citadel hosten

Schnapp dir einen Rechner (Raspberry Pi Zero rockt, Windows-User müssen leider draußen bleiben), steck ein MeshCore USB Companion Radio dran, mach `pip install -r requirements.txt`, pass die `config.yaml` an und hau `python main.py` in die Konsole.

Es spuckt ohne Ende Logs aus (mit `-d` noch mehr). Es schickt beim Start ein Advert, und du musst ein Advert zurückschicken, bevor es mit dir redet.
Erster Login = Sysop-Kräfte! Also logg dich am besten lokal mit `cli_client.py` ein, bevor du das Ding live nimmst. Und wenn's knallt: Einfach die `citadel.db` löschen und von vorn anfangen.

Achtung: Beim ersten Einrichten `database -> use_memory` in der `config.yaml` auf `false` setzen, sonst ist nach nem Crash alles weg. Wenn alles läuft, mach's wieder an (dann rennt die Kiste spürbar schneller).

Hab ich schon erwähnt, dass das hier **super duper ALPHA-Software** ist? Das Ding wird wahrscheinlich abrauchen und deine gesamte Nachrichten-Datenbank fressen. Hab Spaß, aber erwarte noch kein produktives System.

# In-Memory Datenbank Kram

Das In-Memory Ding ist sauschnell auf nem Pi mit SD-Karte, hat aber Tücken:
1. Das BBS speichert ab und zu von selbst auf die Platte. Lies NIEMALS von der Platte, während das BBS läuft.
2. Wenn das BBS abschmiert, sind die neusten Änderungen im Nirvana.
3. Wenn du das Ding abschießt, nutze ^C und WARTE. Das Speichern passiert ganz am Ende.
4. Siehe oben: Erst einrichten (ohne Memory DB), dann hochdrehen.

### Wie fett wird die DB?
Standardmäßig (50 Räume, 300 Nachrichten) sind das popelige 3 MB. Selbst auf nem ollen Pi Zero mit 512 MB RAM ist das n Witz. Die Räume löschen alte Nachrichten eh automatisch (Ringpuffer), also explodiert da auch nix ins Unermessliche.
