"""Klipper/Moonraker printer driver – polls printer status via HTTP API."""

import asyncio
import logging
from typing import Any, Callable

import httpx

from app.plugins.base import BaseDriver

logger = logging.getLogger(__name__)

POLL_INTERVAL = 30


class Driver(BaseDriver):
    driver_key = "klipper"

    def __init__(
        self,
        printer_id: int,
        config: dict[str, Any],
        emitter: Callable[[dict[str, Any]], None],
    ):
        super().__init__(printer_id, config, emitter)
        self._task: asyncio.Task | None = None
        self._printer_state: str = "unknown"

    def validate_config(self) -> None:
        host = self.config.get("host")
        if not host:
            raise ValueError("Klipper driver requires 'host' (Moonraker URL) in driver_config")

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"Klipper driver started for printer {self.printer_id}")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"Klipper driver stopped for printer {self.printer_id}")

    def health(self) -> dict[str, Any]:
        return {
            "driver_key": self.driver_key,
            "printer_id": self.printer_id,
            "running": self._running,
            "printer_state": self._printer_state,
        }

    # ------------------------------------------------------------------ #
    #  Poll loop
    # ------------------------------------------------------------------ #

    async def _poll_loop(self) -> None:
        host = self.config["host"].rstrip("/")
        api_key = self.config.get("api_key", "")
        headers = {}
        if api_key:
            headers["X-Api-Key"] = api_key

        while self._running:
            try:
                async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                    info = await self._get_printer_info(client, host)
                    if info:
                        self._printer_state = info.get("state", "unknown")

                    spoolman = await self._get_spoolman_id(client, host)
                    if spoolman is not None:
                        self.emit({
                            "event_type": "spool_inserted",
                            "slot": {"slot_no": 1},
                            "identifiers": {"external_id": f"spoolman:{spoolman}"},
                        })

            except httpx.RequestError as e:
                logger.debug(f"Klipper poll error for printer {self.printer_id}: {e}")
                self._printer_state = "unreachable"
            except Exception as e:
                logger.warning(f"Klipper poll error for printer {self.printer_id}: {e}")

            try:
                await asyncio.sleep(POLL_INTERVAL)
            except asyncio.CancelledError:
                break

    async def _get_printer_info(self, client: httpx.AsyncClient, host: str) -> dict | None:
        try:
            resp = await client.get(f"{host}/printer/info")
            if resp.status_code == 200:
                return resp.json().get("result", {})
        except Exception:
            pass
        return None

    async def _get_spoolman_id(self, client: httpx.AsyncClient, host: str) -> int | None:
        """Read active spool ID from Moonraker's Spoolman integration."""
        try:
            resp = await client.get(f"{host}/server/spoolman/spool_id")
            if resp.status_code == 200:
                spool_id = resp.json().get("result", {}).get("spool_id")
                if spool_id and int(spool_id) > 0:
                    return int(spool_id)
        except Exception:
            pass
        return None
