# MeshCore Report Bot

A lightweight bot that polls a JSON endpoint for alert data and broadcasts messages to a MeshCore hashtag channel.

## Features

- **Hashtag Channel Broadcasting**: Uses MeshCore's hashtag channel system for fire-and-forget messaging
- **Packet Splitting**: Automatically chunks long messages to fit within LoRa packet size limits
- **Polling Architecture**: Polls a URL periodically instead of webhook callbacks (firewall-friendly)
- **Duplicate Prevention**: Tracks message IDs to avoid re-broadcasting the same alert

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure the bot by editing `bot_config.yaml`:
   - Set your MeshCore serial port and radio parameters
   - Configure the hashtag channel name and index
   - Set the polling URL and interval

3. Run the bot:
   ```bash
   python report_bot.py
   ```

## Configuration

Edit `bot_config.yaml` to customize:

### MeshCore Settings
- `serial_port`: Path to your MeshCore device (e.g., `/dev/ttyUSB0`)
- `frequency`, `bandwidth`, etc.: Radio parameters for your region
- `max_packet_size`: Maximum size for individual packets (default: 140 chars)

### Channel Settings
- `name`: Hashtag channel name (e.g., `#alerts`)
- `index`: Channel index 0-7 on your device

### Polling Settings
- `url`: Endpoint to poll for JSON data
- `interval`: How often to poll in seconds
- `headers`: Optional authentication headers

## Customization

The `process_json_data()` function in `report_bot.py` formats incoming JSON into mesh-ready messages. Modify this function based on your specific JSON structure.

Example JSON processing:
```python
def process_json_data(self, json_data: Dict) -> str:
    message_parts = []

    # Add timestamp
    timestamp = datetime.now().strftime('%m/%d %H:%M')
    message_parts.append(f"[{timestamp}]")

    # Extract your specific fields
    if 'title' in json_data:
        message_parts.append(json_data['title'])

    return "\n".join(message_parts)
```

## Architecture

This bot is designed for a polling architecture where:
1. A simple web service on a shared shell account collects alerts
2. This bot (running inside a firewall) polls that service periodically
3. New alerts are formatted and broadcast to the mesh channel

Channel messages are connectionless and fire-and-forget - no ACK waiting or retry logic needed.

## Logging

The bot logs to stdout with timestamps. Redirect to a file for persistent logs:
```bash
python report_bot.py >> bot.log 2>&1
```