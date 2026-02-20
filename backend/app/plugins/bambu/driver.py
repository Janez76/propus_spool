"""Bambu Lab printer driver – connects via MQTT and reports AMS state."""

import asyncio
import json
import logging
import ssl
import threading
from typing import Any, Callable

import paho.mqtt.client as mqtt

from app.plugins.base import BaseDriver

logger = logging.getLogger(__name__)

MQTT_PORT = 8883
MQTT_USERNAME = "bblp"
RECONNECT_DELAY = 10
AMS_SLOTS_STANDARD = 4
AMS_SLOTS_HT = 1


class Driver(BaseDriver):
    driver_key = "bambu"

    def __init__(
        self,
        printer_id: int,
        config: dict[str, Any],
        emitter: Callable[[dict[str, Any]], None],
    ):
        super().__init__(printer_id, config, emitter)
        self._thread: threading.Thread | None = None
        self._mqtt_client: mqtt.Client | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._last_ams_hash: str | None = None

    def validate_config(self) -> None:
        host = self.config.get("host")
        access_code = self.config.get("access_code")
        serial = self.config.get("serial_number")
        if not host:
            raise ValueError("Bambu driver requires 'host' (printer IP) in driver_config")
        if not access_code:
            raise ValueError("Bambu driver requires 'access_code' in driver_config")
        if not serial:
            raise ValueError("Bambu driver requires 'serial_number' in driver_config")

    async def start(self) -> None:
        self._running = True
        self._loop = asyncio.get_event_loop()
        self._thread = threading.Thread(target=self._mqtt_loop, daemon=True)
        self._thread.start()
        logger.info(f"Bambu driver started for printer {self.printer_id}")

    async def stop(self) -> None:
        self._running = False
        if self._mqtt_client:
            try:
                self._mqtt_client.disconnect()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info(f"Bambu driver stopped for printer {self.printer_id}")

    def health(self) -> dict[str, Any]:
        connected = False
        if self._mqtt_client:
            connected = self._mqtt_client.is_connected()
        return {
            "driver_key": self.driver_key,
            "printer_id": self.printer_id,
            "running": self._running,
            "mqtt_connected": connected,
        }

    # ------------------------------------------------------------------ #
    #  MQTT thread
    # ------------------------------------------------------------------ #

    def _mqtt_loop(self) -> None:
        host = self.config["host"]
        access_code = self.config["access_code"]
        serial = self.config["serial_number"]
        topic = f"device/{serial}/report"

        while self._running:
            try:
                client = mqtt.Client(
                    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                    client_id=f"filaman-{self.printer_id}",
                    protocol=mqtt.MQTTv311,
                )
                client.username_pw_set(MQTT_USERNAME, access_code)

                tls_ctx = ssl.create_default_context()
                tls_ctx.check_hostname = False
                tls_ctx.verify_mode = ssl.CERT_NONE
                client.tls_set_context(tls_ctx)

                client.on_connect = lambda c, ud, flags, rc, props=None: self._on_connect(c, topic, rc)
                client.on_message = lambda c, ud, msg: self._on_message(msg)
                client.on_disconnect = lambda c, ud, flags, rc=None, props=None: self._on_disconnect(rc)

                self._mqtt_client = client
                client.connect(host, MQTT_PORT, keepalive=60)
                client.loop_forever()

            except Exception as e:
                logger.warning(f"Bambu MQTT error for printer {self.printer_id}: {e}")

            if self._running:
                logger.info(f"Bambu reconnecting in {RECONNECT_DELAY}s for printer {self.printer_id}")
                for _ in range(RECONNECT_DELAY * 10):
                    if not self._running:
                        return
                    import time
                    time.sleep(0.1)

    def _on_connect(self, client: mqtt.Client, topic: str, rc: int) -> None:
        if rc == 0:
            logger.info(f"Bambu MQTT connected for printer {self.printer_id}")
            client.subscribe(topic)
        else:
            logger.warning(f"Bambu MQTT connect failed rc={rc} for printer {self.printer_id}")

    def _on_disconnect(self, rc: Any) -> None:
        logger.info(f"Bambu MQTT disconnected (rc={rc}) for printer {self.printer_id}")

    def _on_message(self, msg: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(msg.payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return

        ams_data = payload.get("print", {}).get("ams")
        if not ams_data:
            return

        ams_units_raw = ams_data.get("ams", [])
        if not ams_units_raw:
            return

        ams_hash = json.dumps(ams_units_raw, sort_keys=True)
        if ams_hash == self._last_ams_hash:
            return
        self._last_ams_hash = ams_hash

        ams_units = self._parse_ams_state(ams_units_raw)
        if not ams_units:
            return

        event = {
            "event_type": "ams_state",
            "ams_units": ams_units,
        }

        try:
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(self.emit, event)
            else:
                self.emit(event)
        except Exception as e:
            logger.error(f"Failed to emit ams_state for printer {self.printer_id}: {e}")

    # ------------------------------------------------------------------ #
    #  Parse Bambu AMS data into FilaMan event format
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_ams_state(ams_units_raw: list[dict]) -> list[dict[str, Any]]:
        """Convert Bambu Lab MQTT AMS payload to FilaMan ams_state format."""
        result: list[dict[str, Any]] = []

        for unit in ams_units_raw:
            unit_no = int(unit.get("id", 0))
            trays = unit.get("tray", [])
            slots_total = len(trays) if trays else AMS_SLOTS_STANDARD

            slots: list[dict[str, Any]] = []
            for tray in trays:
                slot_no = int(tray.get("id", 0)) + 1
                tag_uid = tray.get("tag_uid", "")
                tray_type = tray.get("tray_type", "")
                has_rfid = bool(tag_uid and tag_uid.replace("0", ""))
                has_content = bool(tray_type)

                slot_data: dict[str, Any] = {
                    "slot_no": slot_no,
                    "present": has_content,
                }

                if has_content:
                    if has_rfid:
                        slot_data["rfid_uid"] = tag_uid
                    tray_uuid = tray.get("tray_uuid", "")
                    if tray_uuid and tray_uuid.replace("0", ""):
                        slot_data["external_id"] = f"bambu:{tray_uuid}"

                    slot_data["meta"] = {
                        "material": tray_type,
                        "sub_brand": tray.get("tray_sub_brands", ""),
                        "color_hex": tray.get("tray_color", ""),
                        "remain_percent": tray.get("remain"),
                        "weight_g": tray.get("tray_weight"),
                        "diameter_mm": tray.get("tray_diameter"),
                        "nozzle_temp_min": tray.get("nozzle_temp_min"),
                        "nozzle_temp_max": tray.get("nozzle_temp_max"),
                        "bed_temp": tray.get("bed_temp"),
                        "tray_id_name": tray.get("tray_id_name", ""),
                        "humidity": unit.get("humidity"),
                        "temperature": unit.get("temp"),
                    }

                slots.append(slot_data)

            result.append({
                "ams_unit_no": unit_no,
                "slots_total": slots_total,
                "slots": slots,
            })

        return result
