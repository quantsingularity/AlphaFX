"""
WebSocket consumer for live FX rate streaming.
Broadcasts rate updates every 2 seconds to subscribed clients.
"""

import asyncio
import json
import random
from datetime import datetime, timezone

from apps.core.pricing import FALLBACK_RATES, MAJOR_PAIRS, pip_size, spread_pips
from channels.generic.websocket import AsyncWebsocketConsumer


class RateStreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket endpoint: ws://host/ws/rates/{pair}/
    Streams simulated tick updates every 2 seconds.
    Clients can subscribe to specific pairs or "all" for major pairs.
    """

    async def connect(self):
        self.pair = self.scope["url_route"]["kwargs"].get("pair", "all").upper()
        self.group_name = f"rates_{self.pair}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        # Start streaming task
        self.stream_task = asyncio.create_task(self._stream_rates())

    async def disconnect(self, close_code):
        if hasattr(self, "stream_task"):
            self.stream_task.cancel()
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle client messages (e.g., change subscription pair)."""
        try:
            data = json.loads(text_data)
            action = data.get("action")
            if action == "subscribe":
                new_pair = data.get("pair", "all").upper()
                await self.channel_layer.group_discard(
                    self.group_name, self.channel_name
                )
                self.pair = new_pair
                self.group_name = f"rates_{self.pair}"
                await self.channel_layer.group_add(self.group_name, self.channel_name)
                await self.send(json.dumps({"type": "subscribed", "pair": self.pair}))
        except json.JSONDecodeError:
            pass

    async def rate_update(self, event):
        """Handler for group messages from channel layer."""
        await self.send(text_data=json.dumps(event["data"]))

    async def _stream_rates(self):
        """Produce simulated tick data and send to client."""
        pairs = MAJOR_PAIRS if self.pair == "ALL" else [self.pair]
        simulated = {p: FALLBACK_RATES.get(p, 1.0) for p in pairs}

        while True:
            try:
                now = datetime.now(timezone.utc).isoformat()
                ticks = []
                for pair in pairs:
                    spot = simulated[pair]
                    # Simulate micro price movement
                    ps = pip_size(pair)
                    change = random.gauss(0, 1.5) * ps
                    new_spot = round(spot + change, 5)
                    simulated[pair] = new_spot

                    sp = spread_pips(pair)
                    half = sp * ps / 2
                    ticks.append(
                        {
                            "pair": pair,
                            "bid": round(new_spot - half, 5),
                            "ask": round(new_spot + half, 5),
                            "mid": new_spot,
                            "change": round(change / ps, 1),
                            "timestamp": now,
                        }
                    )

                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "tick",
                            "timestamp": now,
                            "ticks": ticks,
                        }
                    )
                )
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(2)
