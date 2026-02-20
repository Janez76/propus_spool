from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession, PrincipalDep, RequirePermission
from app.api.v1.schemas import PaginatedResponse
from app.models import Filament, FilamentColor, Color, Location, Printer, PrinterAmsUnit, PrinterSlot, PrinterSlotAssignment, Spool

router = APIRouter(prefix="/printers", tags=["printers"])


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
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Printer not found"},
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
