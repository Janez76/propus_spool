import importlib
import logging
import time
from datetime import datetime
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models import Printer
from app.plugins.base import BaseDriver
from app.services.ams_slots_service import AmsSlotsService

logger = logging.getLogger(__name__)

MANUAL_RESEND_COOLDOWN = 60


class EventEmitter:
    def __init__(self, printer_id: int, handler: Callable[[dict], None]):
        self.printer_id = printer_id
        self.handler = handler

    def emit(self, event_dict: dict[str, Any]) -> None:
        event_dict["printer_id"] = self.printer_id
        if "event_at" not in event_dict:
            event_dict["event_at"] = datetime.utcnow().isoformat()
        try:
            self.handler(event_dict)
        except Exception as e:
            logger.error(f"Error handling event for printer {self.printer_id}: {e}")


class PluginManager:
    def __init__(self):
        self.drivers: dict[int, BaseDriver] = {}
        self.health_status: dict[int, dict[str, Any]] = {}
        self._manual_resend_timestamps: dict[str, float] = {}

    def _create_event_handler(self, printer_id: int) -> Callable[[dict], None]:
        def handler(event: dict) -> None:
            import asyncio

            asyncio.create_task(self._handle_event(printer_id, event))

        return handler

    async def _handle_event(self, printer_id: int, event: dict) -> None:
        event_type = event.get("event_type")
        event_at_str = event.get("event_at")
        event_at = datetime.fromisoformat(event_at_str) if event_at_str else datetime.utcnow()

        async with async_session_maker() as db:
            try:
                service = AmsSlotsService(db)

                if event_type == "spool_inserted":
                    slot = event.get("slot", {})
                    identifiers = event.get("identifiers", {})
                    await service.apply_spool_inserted(
                        printer_id=printer_id,
                        slot_no=slot.get("slot_no", 1),
                        event_at=event_at,
                        rfid_uid=identifiers.get("rfid_uid"),
                        external_id=identifiers.get("external_id"),
                        ams_unit_no=slot.get("ams_unit_no"),
                        meta=event.get("meta"),
                    )

                elif event_type == "spool_removed":
                    slot = event.get("slot", {})
                    await service.apply_spool_removed(
                        printer_id=printer_id,
                        slot_no=slot.get("slot_no", 1),
                        event_at=event_at,
                        ams_unit_no=slot.get("ams_unit_no"),
                        meta=event.get("meta"),
                    )

                elif event_type == "unknown_spool_detected":
                    slot = event.get("slot", {})
                    identifiers = event.get("identifiers", {})
                    await service.apply_unknown_spool_detected(
                        printer_id=printer_id,
                        slot_no=slot.get("slot_no", 1),
                        event_at=event_at,
                        rfid_uid=identifiers.get("rfid_uid"),
                        external_id=identifiers.get("external_id"),
                        ams_unit_no=slot.get("ams_unit_no"),
                        meta=event.get("meta"),
                    )

                elif event_type == "ams_state":
                    ams_units = event.get("ams_units", [])
                    _events, manual_conflicts = await service.apply_ams_state(
                        printer_id=printer_id,
                        state=ams_units,
                        event_at=event_at,
                    )

                    for conflict in manual_conflicts:
                        await self._resend_manual_filament(conflict)

                logger.info(f"Handled event {event_type} for printer {printer_id}")

            except Exception as e:
                logger.error(f"Error persisting event for printer {printer_id}: {e}")

    def load_driver(self, driver_key: str) -> type[BaseDriver] | None:
        try:
            module = importlib.import_module(f"app.plugins.{driver_key}.driver")
            driver_class = getattr(module, "Driver", None)
            if driver_class and issubclass(driver_class, BaseDriver):
                return driver_class
        except ImportError as e:
            logger.warning(f"Could not load plugin {driver_key}: {e}")
        return None

    async def start_printer(self, printer: Printer) -> bool:
        if printer.id in self.drivers:
            return True

        driver_class = self.load_driver(printer.driver_key)
        if not driver_class:
            logger.error(f"Driver not found: {printer.driver_key}")
            self.health_status[printer.id] = {
                "status": "error",
                "message": f"Driver not found: {printer.driver_key}",
            }
            return False

        emitter = EventEmitter(printer.id, self._create_event_handler(printer.id))
        config = printer.driver_config or {}

        try:
            driver = driver_class(
                printer_id=printer.id,
                config=config,
                emitter=emitter.emit,
            )
            driver.validate_config()
            await driver.start()
            self.drivers[printer.id] = driver
            self.health_status[printer.id] = driver.health()
            logger.info(f"Started driver {printer.driver_key} for printer {printer.id}")
            return True
        except Exception as e:
            logger.error(f"Error starting driver for printer {printer.id}: {e}")
            self.health_status[printer.id] = {
                "status": "error",
                "message": str(e),
            }
            return False

    async def stop_printer(self, printer_id: int) -> None:
        driver = self.drivers.pop(printer_id, None)
        if driver:
            try:
                await driver.stop()
                logger.info(f"Stopped driver for printer {printer_id}")
            except Exception as e:
                logger.error(f"Error stopping driver for printer {printer_id}: {e}")

    async def start_all(self) -> None:
        async with async_session_maker() as db:
            result = await db.execute(
                select(Printer).where(
                    Printer.is_active == True,
                    Printer.deleted_at.is_(None),
                )
            )
            printers = result.scalars().all()

            for printer in printers:
                await self.start_printer(printer)

    async def stop_all(self) -> None:
        for printer_id in list(self.drivers.keys()):
            await self.stop_printer(printer_id)

    async def _resend_manual_filament(self, conflict: dict[str, Any]) -> None:
        """Re-send set_filament for a manually assigned slot that the driver tried to overwrite."""
        printer_id = conflict["printer_id"]
        ams_unit_no = conflict["ams_unit_no"]
        slot_no = conflict["slot_no"]
        assignment = conflict["assignment"]
        meta = assignment.meta or {}

        cooldown_key = f"{printer_id}:{ams_unit_no}:{slot_no}"
        now = time.monotonic()
        last_sent = self._manual_resend_timestamps.get(cooldown_key, 0)
        if now - last_sent < MANUAL_RESEND_COOLDOWN:
            return

        self._manual_resend_timestamps[cooldown_key] = now

        filament_type = meta.get("material", "PLA")
        color_hex = meta.get("color_hex", "FFFFFFFF")

        try:
            await self.send_command(printer_id, {
                "command": "set_filament",
                "ams_id": ams_unit_no,
                "tray_id": slot_no - 1,
                "filament_type": filament_type,
                "color_hex": color_hex,
                "nozzle_temp_min": 190,
                "nozzle_temp_max": 230,
            })
            logger.info(
                f"Re-sent manual filament for printer {printer_id} "
                f"AMS {ams_unit_no} slot {slot_no}: {filament_type}"
            )
        except Exception as e:
            logger.warning(f"Failed to resend manual filament: {e}")

    async def send_command(self, printer_id: int, command: dict[str, Any]) -> bool:
        driver = self.drivers.get(printer_id)
        if not driver:
            logger.warning(f"No active driver for printer {printer_id}")
            return False
        try:
            result = await driver.send_command(command)
            logger.info(f"Sent command {command.get('command')} to printer {printer_id}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error sending command to printer {printer_id}: {e}")
            return False

    def get_health(self) -> dict[int, dict[str, Any]]:
        for printer_id, driver in self.drivers.items():
            self.health_status[printer_id] = driver.health()
        return self.health_status


plugin_manager = PluginManager()
