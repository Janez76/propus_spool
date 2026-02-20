"""Klipper/Moonraker printer driver – polls printer status via HTTP API.

Supports multi-spool setups by reading Klipper save_variables (tN__spool_id)
which map tool numbers to Spoolman spool IDs.
"""

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
        self._initial_state_sent = False
        self._last_slot_spools: dict[int, int | None] = {}

    def validate_config(self) -> None:
        host = self.config.get("host")
        if not host:
            raise ValueError("Klipper driver requires 'host' (Moonraker URL) in driver_config")

    async def start(self) -> None:
        self._running = True
        self._initial_state_sent = False
        self._last_slot_spools = {}
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

    def _emit_initial_state(self) -> None:
        """Emit an ams_state event to create slots for multi-filament printers."""
        if self._initial_state_sent:
            return
        self._initial_state_sent = True

        slots_count = int(self.config.get("slots", 1))
        if slots_count <= 1:
            return

        slots = [{"slot_no": i + 1, "present": False} for i in range(slots_count)]
        self.emit({
            "event_type": "ams_state",
            "ams_units": [{
                "ams_unit_no": 0,
                "slots_total": slots_count,
                "slots": slots,
            }],
        })
        logger.info(f"Klipper initialized {slots_count} slots for printer {self.printer_id}")

    async def _poll_loop(self) -> None:
        host = self.config["host"].rstrip("/")
        if not host.startswith("http://") and not host.startswith("https://"):
            host = f"http://{host}"
        api_key = self.config.get("api_key", "")
        headers = {}
        if api_key:
            headers["X-Api-Key"] = api_key

        self._emit_initial_state()
        slots_count = int(self.config.get("slots", 1))

        while self._running:
            try:
                async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                    info = await self._get_printer_info(client, host)
                    if info:
                        self._printer_state = info.get("state", "unknown")

                    if slots_count > 1:
                        await self._poll_multi_spool(client, host, slots_count)
                    else:
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

    async def _poll_multi_spool(
        self, client: httpx.AsyncClient, host: str, slots_count: int
    ) -> None:
        """Read tN__spool_id variables from Klipper save_variables for each slot."""
        variables = await self._get_save_variables(client, host)
        if variables is None:
            logger.debug(f"Klipper printer {self.printer_id}: save_variables unavailable")
            return

        for tool_idx in range(slots_count):
            slot_no = tool_idx + 1
            key = f"t{tool_idx}__spool_id"
            raw = variables.get(key)

            spool_id: int | None = None
            if raw not in (None, "", 0):
                try:
                    spool_id = int(raw)
                except (ValueError, TypeError):
                    spool_id = None

            prev = self._last_slot_spools.get(slot_no)
            if spool_id == prev:
                continue
            self._last_slot_spools[slot_no] = spool_id

            if spool_id and spool_id > 0:
                self.emit({
                    "event_type": "spool_inserted",
                    "slot": {"slot_no": slot_no, "ams_unit_no": 0},
                    "identifiers": {"external_id": f"spoolman:{spool_id}"},
                })
                logger.info(
                    f"Klipper printer {self.printer_id} slot {slot_no}: "
                    f"spool spoolman:{spool_id}"
                )
            else:
                self.emit({
                    "event_type": "spool_removed",
                    "slot": {"slot_no": slot_no, "ams_unit_no": 0},
                })
                logger.info(
                    f"Klipper printer {self.printer_id} slot {slot_no}: empty"
                )

    async def _get_save_variables(
        self, client: httpx.AsyncClient, host: str
    ) -> dict[str, Any] | None:
        """Query Klipper save_variables via Moonraker objects API."""
        try:
            resp = await client.get(f"{host}/printer/objects/query?save_variables")
            if resp.status_code == 200:
                return (
                    resp.json()
                    .get("result", {})
                    .get("status", {})
                    .get("save_variables", {})
                    .get("variables", {})
                )
            logger.debug(
                f"Klipper printer {self.printer_id}: save_variables status {resp.status_code}"
            )
        except Exception as e:
            logger.debug(f"Klipper printer {self.printer_id}: save_variables error: {e}")
        return None

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
