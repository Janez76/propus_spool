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
        self._print_state: dict[str, Any] = {}
        self._camera_snapshot: bytes | None = None
        self._camera_ts: float = 0

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
            "print_state": dict(self._print_state),
        }

    def get_camera_config(self) -> dict[str, str] | None:
        cam_type = self.config.get("camera_type", "rtsp")
        if cam_type == "none":
            return None

        cam_url = self.config.get("camera_url", "")
        host = self.config.get("host")
        access_code = self.config.get("access_code")

        if cam_url:
            return {"type": cam_type, "url": cam_url}

        if host and access_code:
            return {
                "type": "rtsp",
                "url": f"rtsps://{host}/streaming/live/1",
                "user": MQTT_USERNAME,
                "password": access_code,
            }
        return None

    # ------------------------------------------------------------------ #
    #  Send commands to printer
    # ------------------------------------------------------------------ #

    FILAMENT_TYPE_MAP = {
        "PLA": "GFL99", "PLA-CF": "GFL98", "PETG": "GFB99", "PETG-CF": "GFB98",
        "ABS": "GFS99", "ASA": "GFN99", "TPU": "GFU99", "PA": "GFN98",
        "PC": "GFC99", "PVA": "GFS98", "HIPS": "GFS97", "PET": "GFB97",
    }

    async def send_command(self, command: dict[str, Any]) -> bool:
        if command.get("command") == "set_filament":
            return self._send_filament_setting(command)
        return False

    def _send_filament_setting(self, cmd: dict[str, Any]) -> bool:
        if not self._mqtt_client or not self._mqtt_client.is_connected():
            logger.warning(f"Bambu MQTT not connected for printer {self.printer_id}, cannot send filament setting")
            return False

        serial = self.config["serial_number"]
        topic = f"device/{serial}/request"

        ams_id = cmd.get("ams_id", 0)
        tray_id = cmd.get("tray_id", 0)
        filament_type = cmd.get("filament_type", "PLA")
        color_hex = cmd.get("color_hex", "FFFFFFFF")
        nozzle_min = cmd.get("nozzle_temp_min", 190)
        nozzle_max = cmd.get("nozzle_temp_max", 230)

        base_type = filament_type.split(" ")[0].split("-")[0].upper()
        tray_info_idx = self.FILAMENT_TYPE_MAP.get(filament_type.upper(), self.FILAMENT_TYPE_MAP.get(base_type, "GFL99"))

        payload = json.dumps({
            "print": {
                "command": "ams_filament_setting",
                "ams_id": ams_id,
                "tray_id": tray_id,
                "tray_info_idx": tray_info_idx,
                "tray_color": color_hex.upper() if len(color_hex) == 8 else color_hex.upper() + "FF",
                "nozzle_temp_min": nozzle_min,
                "nozzle_temp_max": nozzle_max,
                "tray_type": filament_type,
                "setting_id": "",
                "reason": "success",
                "sequence_id": "0",
            }
        })

        result = self._mqtt_client.publish(topic, payload)
        logger.info(f"Sent ams_filament_setting to printer {self.printer_id}: AMS {ams_id} tray {tray_id} = {filament_type} ({color_hex})")
        return result.rc == 0

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
                    client_id=f"propus-{self.printer_id}",
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

        print_data = payload.get("print", {})
        if not print_data:
            return

        self._update_print_state(print_data)

        ams_data = print_data.get("ams")
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

    def _update_print_state(self, print_data: dict[str, Any]) -> None:
        """Extract print job status fields from Bambu MQTT payload."""
        field_map = {
            "gcode_state": "gcode_state",
            "subtask_name": "subtask_name",
            "gcode_file": "gcode_file",
            "mc_percent": "mc_percent",
            "mc_remaining_time": "mc_remaining_time",
            "nozzle_temper": "nozzle_temper",
            "nozzle_target_temper": "nozzle_target_temper",
            "bed_temper": "bed_temper",
            "bed_target_temper": "bed_target_temper",
            "layer_num": "layer_num",
            "total_layer_num": "total_layer_num",
            "mc_print_stage": "mc_print_stage",
        }
        for src_key, dst_key in field_map.items():
            val = print_data.get(src_key)
            if val is not None:
                self._print_state[dst_key] = val

    # ------------------------------------------------------------------ #
    #  Parse Bambu AMS data into Propus Spool event format
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_ams_state(ams_units_raw: list[dict]) -> list[dict[str, Any]]:
        """Convert Bambu Lab MQTT AMS payload to Propus Spool ams_state format."""
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
