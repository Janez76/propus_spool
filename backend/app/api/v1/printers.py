import asyncio
import logging
import subprocess
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession, PrincipalDep, RequirePermission
from app.api.v1.schemas import PaginatedResponse
from app.models import Filament, FilamentColor, Color, Location, Printer, PrinterAmsUnit, PrinterSlot, PrinterSlotAssignment, Spool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/printers", tags=["printers"])

_camera_cache: dict[int, tuple[bytes, float]] = {}
CAMERA_CACHE_TTL = 5


class PrinterCreate(BaseModel):
    name: str
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    location_id: int | None = None
    driver_key: str
    driver_config: dict | None = None


class PrinterUpdate(BaseModel):
    name: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    location_id: int | None = None
    is_active: bool | None = None
    driver_key: str | None = None
    driver_config: dict | None = None


class AmsUnitResponse(BaseModel):
    id: int
    printer_id: int
    ams_unit_no: int
    name: str | None
    slots_total: int
    is_active: bool

    class Config:
        from_attributes = True


class SlotAssignmentResponse(BaseModel):
    present: bool = False
    spool_id: int | None = None
    rfid_uid: str | None = None
    external_id: str | None = None
    meta: dict | None = None

    class Config:
        from_attributes = True


class SlotResponse(BaseModel):
    id: int
    printer_id: int
    is_ams_slot: bool
    ams_unit_id: int | None
    slot_no: int
    name: str | None
    is_active: bool
    assignment: SlotAssignmentResponse | None = None

    class Config:
        from_attributes = True


class PrinterResponse(BaseModel):
    id: int
    name: str
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    location_id: int | None
    is_active: bool
    driver_key: str

    class Config:
        from_attributes = True


class PrinterDetailResponse(PrinterResponse):
    driver_config: dict | None = None
    ams_units: list[AmsUnitResponse] = []
    slots: list[SlotResponse] = []


class PrinterStatusResponse(BaseModel):
    id: int
    name: str
    model: str | None = None
    driver_key: str
    is_active: bool
    state: str = "offline"
    job_name: str | None = None
    progress_pct: int | None = None
    remaining_min: int | None = None
    elapsed_min: int | None = None
    nozzle_temp: float | None = None
    nozzle_target: float | None = None
    bed_temp: float | None = None
    bed_target: float | None = None
    layer: int | None = None
    total_layers: int | None = None
    has_camera: bool = False


@router.get("/status", response_model=list[PrinterStatusResponse])
async def get_printers_status(
    db: DBSession,
    principal: PrincipalDep,
):
    from app.plugins.manager import plugin_manager

    result = await db.execute(
        select(Printer).where(Printer.deleted_at.is_(None), Printer.is_active == True)
    )
    printers = result.scalars().all()
    all_status = plugin_manager.get_all_printer_status()

    out: list[dict] = []
    for p in printers:
        ps = all_status.get(p.id, {})
        has_camera = plugin_manager.get_camera_config(p.id) is not None

        if p.driver_key == "bambu":
            gcode_state = ps.get("gcode_state", "IDLE")
            state_map = {"RUNNING": "printing", "PAUSE": "paused", "FAILED": "error", "FINISH": "idle", "IDLE": "idle", "PREPARE": "preparing"}
            state = state_map.get(gcode_state, "idle")
            job = ps.get("subtask_name") or ps.get("gcode_file") or None
            progress = ps.get("mc_percent")
            remaining = ps.get("mc_remaining_time")
            nozzle = ps.get("nozzle_temper")
            nozzle_t = ps.get("nozzle_target_temper")
            bed = ps.get("bed_temper")
            bed_t = ps.get("bed_target_temper")
            layer = ps.get("layer_num")
            total_layers = ps.get("total_layer_num")
            elapsed = None
        elif p.driver_key == "klipper":
            kstate = ps.get("state", "standby")
            state_map = {"printing": "printing", "paused": "paused", "error": "error", "complete": "idle", "standby": "idle", "cancelled": "idle"}
            state = state_map.get(kstate, "idle")
            job = ps.get("filename") or None
            progress = ps.get("progress")
            dur = ps.get("print_duration", 0)
            elapsed = round(dur / 60) if dur else None
            remaining = None
            nozzle = ps.get("nozzle_temp")
            nozzle_t = ps.get("nozzle_target")
            bed = ps.get("bed_temp")
            bed_t = ps.get("bed_target")
            layer = None
            total_layers = None
        else:
            state = "offline"
            job = None
            progress = None
            remaining = None
            elapsed = None
            nozzle = nozzle_t = bed = bed_t = None
            layer = total_layers = None

        if not ps:
            state = "offline"

        out.append(PrinterStatusResponse(
            id=p.id,
            name=p.name,
            model=p.model,
            driver_key=p.driver_key,
            is_active=p.is_active,
            state=state,
            job_name=job,
            progress_pct=int(progress) if progress is not None else None,
            remaining_min=int(remaining) if remaining is not None else None,
            elapsed_min=elapsed,
            nozzle_temp=round(nozzle, 1) if nozzle is not None else None,
            nozzle_target=round(nozzle_t, 1) if nozzle_t is not None else None,
            bed_temp=round(bed, 1) if bed is not None else None,
            bed_target=round(bed_t, 1) if bed_t is not None else None,
            layer=layer,
            total_layers=total_layers,
            has_camera=has_camera,
        ).model_dump())

    return out


@router.get("/{printer_id}/camera")
async def get_camera_snapshot(
    printer_id: int,
    db: DBSession,
    principal: PrincipalDep,
):
    from app.plugins.manager import plugin_manager

    cam = plugin_manager.get_camera_config(printer_id)
    if not cam:
        raise HTTPException(status_code=404, detail="No camera available for this printer")

    now = time.time()
    cached = _camera_cache.get(printer_id)
    if cached and (now - cached[1]) < CAMERA_CACHE_TTL:
        return Response(content=cached[0], media_type="image/jpeg")

    url = cam["url"]
    user = cam.get("user", "")
    password = cam.get("password", "")

    try:
        jpeg_bytes = await asyncio.get_event_loop().run_in_executor(
            None, _grab_rtsp_frame, url, user, password
        )
        if jpeg_bytes:
            _camera_cache[printer_id] = (jpeg_bytes, now)
            return Response(content=jpeg_bytes, media_type="image/jpeg")
    except Exception as e:
        logger.warning(f"Camera snapshot failed for printer {printer_id}: {e}")

    raise HTTPException(status_code=503, detail="Camera snapshot unavailable")


def _grab_rtsp_frame(url: str, user: str, password: str) -> bytes | None:
    """Use ffmpeg to grab a single JPEG frame from RTSP stream."""
    rtsp_url = url
    if user and password:
        proto, rest = url.split("://", 1)
        rtsp_url = f"{proto}://{user}:{password}@{rest}"

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-rtsp_transport", "tcp",
                "-i", rtsp_url,
                "-frames:v", "1",
                "-q:v", "2",
                tmp_path,
            ],
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            data = Path(tmp_path).read_bytes()
            if data:
                return data
    except subprocess.TimeoutExpired:
        logger.warning("ffmpeg RTSP snapshot timed out")
    except FileNotFoundError:
        logger.warning("ffmpeg not found – camera snapshots disabled")
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
    return None


@router.get("", response_model=PaginatedResponse[PrinterResponse])
async def list_printers(
    db: DBSession,
    principal: PrincipalDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    query = select(Printer).where(Printer.deleted_at.is_(None)).order_by(Printer.name)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().all()

    count_query = select(func.count()).select_from(Printer).where(Printer.deleted_at.is_(None))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return PaginatedResponse(items=items, page=page, page_size=page_size, total=total)


@router.post("", response_model=PrinterResponse, status_code=status.HTTP_201_CREATED)
async def create_printer(
    data: PrinterCreate,
    db: DBSession,
    principal = RequirePermission("printers:create"),
):
    if data.location_id:
        result = await db.execute(select(Location).where(Location.id == data.location_id))
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "validation_error", "message": "Location not found"},
            )

    dump = data.model_dump()
    if dump.get("driver_key") in ("bambu",) and dump.get("serial_number"):
        cfg = dump.get("driver_config") or {}
        cfg.setdefault("serial_number", dump["serial_number"])
        dump["driver_config"] = cfg

    printer = Printer(**dump)
    db.add(printer)
    await db.commit()
    await db.refresh(printer)

    from app.plugins.manager import plugin_manager
    await plugin_manager.start_printer(printer)

    return printer


@router.get("/{printer_id}", response_model=PrinterDetailResponse)
async def get_printer(
    printer_id: int,
    db: DBSession,
    principal: PrincipalDep,
):
    result = await db.execute(
        select(Printer)
        .where(Printer.id == printer_id, Printer.deleted_at.is_(None))
        .options(
            selectinload(Printer.ams_units),
            selectinload(Printer.slots).selectinload(PrinterSlot.assignment),
        )
    )
    printer = result.scalar_one_or_none()

    if not printer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Printer not found"},
        )

    return printer


@router.patch("/{printer_id}", response_model=PrinterResponse)
async def update_printer(
    printer_id: int,
    data: PrinterUpdate,
    db: DBSession,
    principal = RequirePermission("printers:update"),
):
    result = await db.execute(
        select(Printer).where(Printer.id == printer_id, Printer.deleted_at.is_(None))
    )
    printer = result.scalar_one_or_none()

    if not printer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Printer not found"},
        )

    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(printer, key, value)

    if printer.driver_key == "bambu" and printer.serial_number:
        cfg = printer.driver_config or {}
        cfg.setdefault("serial_number", printer.serial_number)
        printer.driver_config = cfg

    await db.commit()
    await db.refresh(printer)

    from app.plugins.manager import plugin_manager
    await plugin_manager.stop_printer(printer.id)
    if printer.is_active:
        await plugin_manager.start_printer(printer)

    return printer


@router.delete("/{printer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_printer(
    printer_id: int,
    db: DBSession,
    principal = RequirePermission("printers:delete"),
):
    from datetime import datetime

    result = await db.execute(
        select(Printer).where(Printer.id == printer_id, Printer.deleted_at.is_(None))
    )
    printer = result.scalar_one_or_none()

    if not printer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Printer not found"},
        )

    printer.deleted_at = datetime.utcnow()
    await db.commit()


@router.post("/{printer_id}/ams-units", response_model=AmsUnitResponse, status_code=status.HTTP_201_CREATED)
async def create_ams_unit(
    printer_id: int,
    ams_unit_no: int,
    slots_total: int,
    name: str | None = None,
    db: DBSession = None,
    principal = RequirePermission("printers:update"),
):
    result = await db.execute(
        select(Printer).where(Printer.id == printer_id, Printer.deleted_at.is_(None))
    )
    printer = result.scalar_one_or_none()
    if not printer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Printer not found"},
        )

    max_ams = (printer.driver_config or {}).get("max_ams_units")
    if max_ams is not None:
        count_result = await db.execute(
            select(func.count()).select_from(PrinterAmsUnit).where(
                PrinterAmsUnit.printer_id == printer_id
            )
        )
        current_count = count_result.scalar() or 0
        if current_count >= int(max_ams):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "max_ams_reached",
                    "message": f"Maximale Anzahl AMS-Einheiten erreicht ({max_ams})",
                },
            )

    ams_unit = PrinterAmsUnit(
        printer_id=printer_id,
        ams_unit_no=ams_unit_no,
        name=name,
        slots_total=slots_total,
    )
    db.add(ams_unit)
    await db.commit()
    await db.refresh(ams_unit)
    return ams_unit


@router.delete("/{printer_id}/ams-units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ams_unit(
    printer_id: int,
    unit_id: int,
    db: DBSession = None,
    principal=RequirePermission("printers:update"),
):
    result = await db.execute(
        select(PrinterAmsUnit).where(
            PrinterAmsUnit.id == unit_id,
            PrinterAmsUnit.printer_id == printer_id,
        )
    )
    ams_unit = result.scalar_one_or_none()

    if not ams_unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "AMS unit not found"},
        )

    await db.delete(ams_unit)
    await db.commit()


class SlotAssignRequest(BaseModel):
    spool_id: int | None = None


@router.put("/{printer_id}/ams-units/{unit_id}/slots/{slot_no}/assign")
async def assign_spool_to_slot(
    printer_id: int,
    unit_id: int,
    slot_no: int,
    body: SlotAssignRequest,
    db: DBSession = None,
    principal=RequirePermission("printers:update"),
):
    from datetime import datetime as dt

    result = await db.execute(
        select(PrinterAmsUnit).where(
            PrinterAmsUnit.id == unit_id,
            PrinterAmsUnit.printer_id == printer_id,
        )
    )
    ams_unit = result.scalar_one_or_none()
    if not ams_unit:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "AMS unit not found"})

    spool_meta: dict | None = None
    if body.spool_id is not None:
        result = await db.execute(
            select(Spool)
            .where(Spool.id == body.spool_id, Spool.deleted_at.is_(None))
            .options(
                selectinload(Spool.filament).selectinload(Filament.filament_colors).selectinload(FilamentColor.color)
            )
        )
        spool = result.scalar_one_or_none()
        if not spool:
            raise HTTPException(status_code=400, detail={"code": "validation_error", "message": "Spool not found"})

        fil = spool.filament
        color_hex = ""
        if fil and fil.filament_colors:
            first_color = sorted(fil.filament_colors, key=lambda c: c.position)[0]
            if first_color.color:
                color_hex = first_color.color.hex_code.lstrip("#") + "FF"

        remain_pct = None
        if spool.remaining_weight_g is not None and spool.initial_total_weight_g:
            empty = spool.empty_spool_weight_g or 0
            net_initial = spool.initial_total_weight_g - empty
            if net_initial > 0:
                remain_pct = round((spool.remaining_weight_g / net_initial) * 100)

        spool_meta = {
            "material": fil.type if fil else "",
            "designation": fil.designation if fil else "",
            "color_hex": color_hex,
            "remain_percent": remain_pct,
            "weight_g": str(int(spool.remaining_weight_g)) if spool.remaining_weight_g else None,
            "source": "manual",
        }

    result = await db.execute(
        select(PrinterSlot).where(
            PrinterSlot.printer_id == printer_id,
            PrinterSlot.is_ams_slot == True,
            PrinterSlot.ams_unit_id == unit_id,
            PrinterSlot.slot_no == slot_no,
        )
    )
    slot = result.scalar_one_or_none()

    if not slot:
        slot = PrinterSlot(
            printer_id=printer_id,
            is_ams_slot=True,
            ams_unit_id=unit_id,
            slot_no=slot_no,
        )
        db.add(slot)
        await db.flush()

    result = await db.execute(
        select(PrinterSlotAssignment).where(PrinterSlotAssignment.slot_id == slot.id)
    )
    assignment = result.scalar_one_or_none()

    if not assignment:
        assignment = PrinterSlotAssignment(slot_id=slot.id)
        db.add(assignment)

    if body.spool_id is not None:
        assignment.spool_id = body.spool_id
        assignment.present = True
        assignment.inserted_at = dt.utcnow()
        assignment.meta = spool_meta
    else:
        assignment.spool_id = None
        assignment.present = False
        assignment.rfid_uid = None
        assignment.external_id = None
        assignment.meta = None

    assignment.updated_at = dt.utcnow()
    await db.commit()

    from app.plugins.manager import plugin_manager

    result = await db.execute(
        select(Printer).where(Printer.id == printer_id)
    )
    printer_obj = result.scalar_one_or_none()

    if printer_obj and printer_obj.driver_key == "bambu" and body.spool_id is not None and spool_meta:
        fil = spool.filament if spool else None
        await plugin_manager.send_command(printer_id, {
            "command": "set_filament",
            "ams_id": ams_unit.ams_unit_no,
            "tray_id": slot_no - 1,
            "filament_type": fil.type if fil else "PLA",
            "color_hex": spool_meta.get("color_hex", "FFFFFFFF"),
            "nozzle_temp_min": 190,
            "nozzle_temp_max": 230,
        })

    if printer_obj and printer_obj.driver_key == "klipper":
        tool_index = slot_no - 1
        if body.spool_id is not None:
            ext_id = spool.external_id if spool else None
            spoolman_id = body.spool_id
            if ext_id and ext_id.startswith("spoolman:"):
                try:
                    spoolman_id = int(ext_id.split(":")[1])
                except (ValueError, IndexError):
                    pass
            await plugin_manager.send_command(printer_id, {
                "command": "set_spool",
                "tool_index": tool_index,
                "spool_id": spoolman_id,
            })
            assignment.external_id = f"spoolman:{spoolman_id}"
            await db.commit()
        else:
            await plugin_manager.send_command(printer_id, {
                "command": "clear_spool",
                "tool_index": tool_index,
            })

    return {"ok": True, "slot_no": slot_no, "spool_id": body.spool_id}


@router.get("/{printer_id}/ams-units", response_model=list[AmsUnitResponse])
async def list_ams_units(
    printer_id: int,
    db: DBSession,
    principal: PrincipalDep,
):
    result = await db.execute(
        select(PrinterAmsUnit).where(PrinterAmsUnit.printer_id == printer_id).order_by(PrinterAmsUnit.ams_unit_no)
    )
    return result.scalars().all()


@router.get("/{printer_id}/slots", response_model=list[SlotResponse])
async def list_slots(
    printer_id: int,
    db: DBSession,
    principal: PrincipalDep,
):
    result = await db.execute(
        select(PrinterSlot).where(PrinterSlot.printer_id == printer_id).order_by(PrinterSlot.slot_no)
    )
    return result.scalars().all()
