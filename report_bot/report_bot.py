#!/usr/bin/env python3
"""
Lightweight MeshCore Channel Bot
Polls for JSON data from a simple service and broadcasts to hashtag channels.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, UTC
from typing import Dict, List, Optional

import yaml
import aiohttp
from meshcore import MeshCore, EventType
from serial import SerialException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


class MeshCoreChannelBot:
    """Lightweight bot that polls for JSON data and broadcasts to mesh channels."""

    def __init__(self, config_file: str = "bot_config.yaml"):
        self.config = self._load_config(config_file)
        self.meshcore: Optional[MeshCore] = None
        self._running = False
        self._channel_configured = False

    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            # Default config if file doesn't exist
            return {
                'meshcore': {
                    'serial_port': '/dev/ttyUSB0',
                    'baud_rate': 115200,
                    'frequency': 910.525,
                    'bandwidth': 62.5,
                    'spreading_factor': 7,
                    'coding_rate': 5,
                    'tx_power': 22,
                    'name': 'Channel Bot',
                    'max_packet_size': 140,
                    'inter_packet_delay': 0.5
                },
                'channel': {
                    'name': '#alerts',  # Hashtag channel name
                    'index': 0          # Channel index (0-7)
                },
                'polling': {
                    'url': 'https://example.com/api/alerts/latest',
                    'interval': 60,     # Poll every 60 seconds
                    'headers': {}       # Optional authentication headers
                }
            }

    async def start_meshcore(self):
        """Initialize and configure MeshCore device."""
        mc_config = self.config['meshcore']

        serial_port = mc_config.get('serial_port', '/dev/ttyUSB0')
        baud_rate = mc_config.get('baud_rate', 115200)

        log.info(f"Connecting MeshCore at {serial_port}")

        # Create MeshCore instance
        debug = log.getEffectiveLevel() <= logging.DEBUG
        self.meshcore = await MeshCore.create_serial(serial_port, baud_rate, debug=debug)

        # Configure radio parameters
        frequency = mc_config.get('frequency', 910.525)
        bandwidth = mc_config.get('bandwidth', 62.5)
        spreading_factor = mc_config.get('spreading_factor', 7)
        coding_rate = mc_config.get('coding_rate', 5)
        tx_power = mc_config.get('tx_power', 22)
        node_name = mc_config.get('name', 'Channel Bot')

        # Set time
        now = int(time.time())
        await self.meshcore.commands.set_time(now)

        # Configure radio
        result = await self.meshcore.commands.set_radio(
            frequency, bandwidth, spreading_factor, coding_rate
        )
        if result.type == EventType.ERROR:
            raise RuntimeError(f"Failed to set radio parameters: {result.payload}")

        # Set TX power
        result = await self.meshcore.commands.set_tx_power(tx_power)
        if result.type == EventType.ERROR:
            raise RuntimeError(f"Failed to set TX power: {result.payload}")

        # Set node name
        result = await self.meshcore.commands.set_name(node_name)
        if result.type == EventType.ERROR:
            raise RuntimeError(f"Failed to set node name: {result.payload}")

        # Ensure contacts
        await self.meshcore.ensure_contacts()

        # Configure the hashtag channel
        await self._configure_channel()

        log.info("MeshCore initialized successfully")

    async def _configure_channel(self):
        """Configure the hashtag channel."""
        channel_config = self.config['channel']
        channel_name = channel_config['name']
        channel_index = channel_config['index']

        log.info(f"Configuring channel {channel_index}: '{channel_name}'")

        # Set the channel - meshcore will automatically generate the key from the hashtag
        result = await self.meshcore.commands.set_channel(channel_index, channel_name)

        if result.type == EventType.ERROR:
            raise RuntimeError(f"Failed to configure channel: {result.payload}")

        self._channel_configured = True
        log.info(f"Channel '{channel_name}' configured on index {channel_index}")

    def _chunk_message(self, message: str, max_packet_length: int = 140) -> List[str]:
        """Split message into chunks that fit within packet size limits.

        For channels, we don't need ACK space reservation, but we still
        need to respect the packet size limits.
        """
        if not message:
            return [""]

        words = message.split(" ")
        approx_chunks = len(message) / max_packet_length

        # Reserve space for packet numbering suffix if needed
        if approx_chunks >= 10:
            max_packet_length -= len('[xx/xx]')
        elif approx_chunks > 1:
            max_packet_length -= len('[x/x]')

        chunks = []
        chunk = []
        chunk_size = 0

        for word in words:
            word_len = len(word)
            if chunk_size + word_len + 1 < max_packet_length:
                chunk.append(word)
                chunk_size += word_len + 1
            else:
                chunks.append(" ".join(chunk))
                chunk = [word]
                chunk_size = word_len + 1

        if chunk:
            chunks.append(" ".join(chunk))

        # Add packet numbering if multiple chunks
        if len(chunks) > 1:
            for i in range(len(chunks)):
                chunks[i] += f'[{i+1}/{len(chunks)}]'

        return chunks

    async def send_channel_message(self, message: str) -> bool:
        """Send message to configured channel, splitting into packets if needed."""
        if not self.meshcore or not self._channel_configured:
            log.error("MeshCore or channel not configured")
            return False

        channel_index = self.config['channel']['index']
        max_packet_size = self.config['meshcore'].get('max_packet_size', 140)
        chunks = self._chunk_message(message, max_packet_size)
        inter_packet_delay = self.config['meshcore'].get('inter_packet_delay', 0.5)

        success = True
        for i, chunk in enumerate(chunks):
            log.info(f"Sending channel packet {i+1}/{len(chunks)}: {chunk[:50]}...")

            # Channel messages are fire-and-forget
            result = await self.meshcore.commands.send_chan_msg(channel_index, chunk)

            if result.type == EventType.ERROR:
                log.error(f"Failed to send channel packet {i+1}: {result.payload}")
                success = False
            else:
                log.debug(f"Channel packet {i+1} sent successfully")

            if i < len(chunks) - 1:  # Don't delay after last packet
                await asyncio.sleep(inter_packet_delay)

        return success

    def process_json_data(self, json_data: Dict) -> str:
        """
        PLACEHOLDER: Process incoming JSON data and format for mesh transmission.

        Args:
            json_data: Raw JSON data from polling service

        Returns:
            Formatted message string ready for mesh transmission

        TODO: Implement based on your specific JSON format and requirements
        """
        # Example implementation - customize based on your JSON format
        message_parts = []

        # Add timestamp
        timestamp = datetime.now().strftime('%m/%d %H:%M')
        message_parts.append(f"[{timestamp}]")

        # Extract and format relevant fields
        # This is just an example - modify based on your JSON structure
        if 'alert_type' in json_data:
            message_parts.append(f"🚨 {json_data['alert_type']}")

        if 'title' in json_data:
            message_parts.append(json_data['title'])

        if 'message' in json_data:
            message_parts.append(json_data['message'])

        if 'severity' in json_data:
            severity_emoji = {
                'critical': '🔴',
                'warning': '🟡',
                'info': '🔵'
            }.get(json_data['severity'].lower(), '⚪')
            message_parts.append(f"Priority: {severity_emoji} {json_data['severity']}")

        return "\n".join(message_parts)

    async def poll_for_data(self):
        """Poll the configured URL for new data."""
        polling_config = self.config['polling']
        url = polling_config['url']
        headers = polling_config.get('headers', {})

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        json_data = await response.json()
                        log.debug(f"Received data: {json_data}")
                        return json_data
                    else:
                        log.warning(f"HTTP {response.status} from {url}")
                        return None
        except Exception as e:
            log.error(f"Error polling {url}: {e}")
            return None

    async def polling_loop(self):
        """Main polling loop."""
        interval = self.config['polling']['interval']
        last_message_id = None  # Track last processed message to avoid duplicates

        while self._running:
            try:
                # Poll for new data
                json_data = await self.poll_for_data()

                if json_data:
                    # Check for duplicate message (adjust field name based on your JSON structure)
                    current_message_id = json_data.get('id') or json_data.get('timestamp')

                    if current_message_id != last_message_id:
                        # Process and send new message
                        message = self.process_json_data(json_data)

                        if message:
                            log.info("New alert received, broadcasting to channel...")
                            success = await self.send_channel_message(message)

                            if success:
                                log.info("Alert broadcast successfully")
                                last_message_id = current_message_id
                            else:
                                log.error("Failed to broadcast alert")
                        else:
                            log.warning("No message generated from JSON data")
                    else:
                        log.debug("No new messages")

            except Exception as e:
                log.exception(f"Error in polling loop: {e}")

            # Wait for next poll
            await asyncio.sleep(interval)

    async def start(self):
        """Start the bot."""
        try:
            log.info("Starting MeshCore Channel Bot...")
            await self.start_meshcore()
            self._running = True

            # Start polling loop
            log.info(f"Starting polling loop (interval: {self.config['polling']['interval']}s)")
            await self.polling_loop()

        except Exception as e:
            log.exception(f"Failed to start bot: {e}")
            raise

    async def stop(self):
        """Stop the bot."""
        if self._running:
            log.info("Stopping bot...")
            self._running = False
            if self.meshcore:
                await self.meshcore.disconnect()
            log.info("Bot stopped")


async def main():
    """Main entry point."""
    bot = MeshCoreChannelBot()

    try:
        await bot.start()
    except KeyboardInterrupt:
        log.info("Received shutdown signal")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())