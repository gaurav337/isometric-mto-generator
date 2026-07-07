import logging
import re
from typing import Any
from app.schemas import (
    DrawingMetadata,
    MTOItem,
    MTOSummary,
    MTOResponse,
    ItemCategory,
    ItemUnit,
    JobStatus
)

logger = logging.getLogger(__name__)

def validate_and_derive(raw_data: dict[str, Any], job_id: str) -> MTOResponse:
    """
    Validates the raw LLM output, normalizes units and sizes,
    derives GASKET and BOLT sets based on flanged joints,
    recomputes the MTO summary, and returns a verified MTOResponse.
    """
    # 1. Parse and validate DrawingMetadata
    raw_meta = raw_data.get("drawing_meta", {})
    if not isinstance(raw_meta, dict):
        raw_meta = {}
        
    try:
        drawing_meta = DrawingMetadata(
            drawing_no=str(raw_meta.get("drawing_no") or "UNKNOWN-DWG"),
            revision=str(raw_meta.get("revision") or "0"),
            line_number=str(raw_meta.get("line_number") or "UNKNOWN-LINE"),
            nps=str(raw_meta.get("nps") or 'UNKNOWN-NPS"'),
            material_class=str(raw_meta.get("material_class") or "UNKNOWN-CLASS"),
            service=str(raw_meta.get("service") or "UNKNOWN-SERVICE"),
            design_pressure=raw_meta.get("design_pressure"),
            design_temperature=raw_meta.get("design_temperature")
        )
    except Exception as e:
        logger.warning(f"Error parsing metadata, using defaults: {str(e)}")
        drawing_meta = DrawingMetadata(
            drawing_no="UNKNOWN-DWG",
            revision="0",
            line_number="UNKNOWN-LINE",
            nps='UNKNOWN-NPS"',
            material_class="UNKNOWN-CLASS",
            service="UNKNOWN-SERVICE"
        )

    # 2. Parse MTO items
    raw_items = raw_data.get("items", [])
    if not isinstance(raw_items, list):
        raw_items = []

    validated_items: list[MTOItem] = []
    
    # Track counts for derivation
    flange_qty = 0.0
    flanged_valve_qty = 0.0
    existing_gasket_qty = 0.0
    existing_bolt_qty = 0.0
    
    # Store sizes and ratings of flanges to copy to derived gaskets/bolts
    flange_sizes: list[str] = []
    flange_ratings: list[str] = []
    flange_materials: list[str] = []

    # Map raw strings to ItemCategory enum
    category_map = {
        "PIPE": ItemCategory.PIPE,
        "FITTING": ItemCategory.FITTING,
        "FLANGE": ItemCategory.FLANGE,
        "VALVE": ItemCategory.VALVE,
        "GASKET": ItemCategory.GASKET,
        "BOLT": ItemCategory.BOLT,
        "SUPPORT": ItemCategory.SUPPORT,
        "WELD": ItemCategory.WELD
    }

    for idx, raw_item in enumerate(raw_items):
        if not isinstance(raw_item, dict):
            continue
            
        try:
            # Parse raw category
            raw_cat = str(raw_item.get("category", "")).upper().strip()
            category = category_map.get(raw_cat)
            if not category:
                # Fallback matching
                if "PIPE" in raw_cat:
                    category = ItemCategory.PIPE
                elif "ELBOW" in raw_cat or "TEE" in raw_cat or "REDUCER" in raw_cat or "CAP" in raw_cat or "FITTING" in raw_cat:
                    category = ItemCategory.FITTING
                elif "FLANGE" in raw_cat:
                    category = ItemCategory.FLANGE
                elif "VALVE" in raw_cat:
                    category = ItemCategory.VALVE
                elif "GASKET" in raw_cat:
                    category = ItemCategory.GASKET
                elif "BOLT" in raw_cat or "STUD" in raw_cat:
                    category = ItemCategory.BOLT
                elif "SUPPORT" in raw_cat or "SHOE" in raw_cat:
                    category = ItemCategory.SUPPORT
                elif "WELD" in raw_cat:
                    category = ItemCategory.WELD
                else:
                    logger.warning(f"Unknown item category: {raw_cat}, skipping item.")
                    continue

            # Parse and validate quantity
            try:
                quantity = float(raw_item.get("quantity", 0))
            except (ValueError, TypeError):
                quantity = 0.0

            # Enforce Unit based on Category (do not trust LLM)
            if category == ItemCategory.PIPE:
                unit = ItemUnit.M
            elif category == ItemCategory.BOLT:
                unit = ItemUnit.SET
            else:
                unit = ItemUnit.EA

            # Handle length_m
            length_m = None
            if category == ItemCategory.PIPE:
                # If length_m is not set but quantity is set, assign quantity to length_m
                length_m = raw_item.get("length_m")
                try:
                    if length_m is not None:
                        length_m = float(length_m)
                    else:
                        length_m = quantity
                except (ValueError, TypeError):
                    length_m = quantity
                
                # Check for positive length
                if length_m <= 0:
                    length_m = 1.0  # default minimum fallback
                    quantity = 1.0
            
            # Normalize NPS size
            size_nps = str(raw_item.get("size_nps") or "").strip()
            # Standardize X/x to lowercase x
            size_nps = size_nps.replace("X", "x")
            # If no double quote, append it
            if size_nps and '"' not in size_nps:
                # E.g., if "6" or "6x4", convert to "6\"" or "6\"x4\""
                size_nps = size_nps.replace("x", "\"x") + "\""
                size_nps = size_nps.replace("\"\"", "\"")  # guard against double quotes
            
            # If it's still empty, use nominal size from drawing metadata
            if not size_nps or size_nps == "\"":
                size_nps = drawing_meta.nps if drawing_meta.nps else "6\""

            # Parse confidence
            try:
                confidence = float(raw_item.get("confidence", 0.90))
            except (ValueError, TypeError):
                confidence = 0.90

            item = MTOItem(
                item_no=len(validated_items) + 1,
                category=category,
                description=str(raw_item.get("description") or f"{category.value} component"),
                size_nps=size_nps,
                schedule_rating=raw_item.get("schedule_rating"),
                material_spec=raw_item.get("material_spec"),
                end_type=raw_item.get("end_type"),
                quantity=quantity,
                unit=unit,
                length_m=length_m,
                confidence=confidence,
                remarks=str(raw_item.get("remarks") or "")
            )
            validated_items.append(item)

            # Accumulate values for GASKET / BOLT derivation
            if category == ItemCategory.FLANGE:
                flange_qty += quantity
                if item.size_nps:
                    flange_sizes.append(item.size_nps)
                if item.schedule_rating:
                    flange_ratings.append(item.schedule_rating)
                if item.material_spec:
                    flange_materials.append(item.material_spec)
            elif category == ItemCategory.VALVE:
                # Count flanged valves
                desc = item.description.lower()
                end = str(item.end_type or "").upper()
                if end == "FLGD" or "flanged" in desc or "flange" in desc:
                    flanged_valve_qty += quantity
            elif category == ItemCategory.GASKET:
                existing_gasket_qty += quantity
            elif category == ItemCategory.BOLT:
                existing_bolt_qty += quantity

        except Exception as e:
            logger.warning(f"Failed to validate item at index {idx}: {str(e)}")
            continue

    # 3. Gasket and Stud Bolt derivation
    # Rule: 1 gasket + 1 bolt set per flanged joint.
    # Total joints = flange count + flanged valve count.
    # Reconcile counts rather than blindly appending.
    total_joints_required = flange_qty + flanged_valve_qty
    
    # Gather default specs from existing flanges
    default_size = flange_sizes[0] if flange_sizes else (drawing_meta.nps if drawing_meta.nps else "6\"")
    default_rating = flange_ratings[0] if flange_ratings else "CL150"
    default_material = flange_materials[0] if flange_materials else "ASTM A105"

    # Reconcile Gaskets
    if existing_gasket_qty < total_joints_required:
        needed_gaskets = total_joints_required - existing_gasket_qty
        gasket_item = MTOItem(
            item_no=len(validated_items) + 1,
            category=ItemCategory.GASKET,
            description="Spiral Wound Gasket, SS316/Graphite, 1/8\" thk, ASME B16.20",
            size_nps=default_size,
            schedule_rating=default_rating,
            material_spec="ASME B16.20",
            end_type=None,
            quantity=needed_gaskets,
            unit=ItemUnit.EA,
            length_m=None,
            confidence=0.90,
            remarks=f"[Derived programmatically: {needed_gaskets} required based on {total_joints_required} flanged joints]"
        )
        validated_items.append(gasket_item)
    elif existing_gasket_qty > total_joints_required:
        # If LLM predicted too many, we keep them but add a warning remark
        for item in validated_items:
            if item.category == ItemCategory.GASKET:
                item.remarks = (item.remarks + " [Reconciled: quantity exceeds computed flange joints]").strip()

    # Reconcile Bolt Sets
    if existing_bolt_qty < total_joints_required:
        needed_bolts = total_joints_required - existing_bolt_qty
        bolt_item = MTOItem(
            item_no=len(validated_items) + 1,
            category=ItemCategory.BOLT,
            description="Stud Bolt with Nuts, ASTM A193 B7 / A194 2H, CL150",
            size_nps=default_size,
            schedule_rating=default_rating,
            material_spec="ASTM A193 B7 / A194 2H",
            end_type=None,
            quantity=needed_bolts,
            unit=ItemUnit.SET,
            length_m=None,
            confidence=0.90,
            remarks=f"[Derived programmatically: {needed_bolts} sets required based on {total_joints_required} flanged joints]"
        )
        validated_items.append(bolt_item)
    elif existing_bolt_qty > total_joints_required:
        for item in validated_items:
            if item.category == ItemCategory.BOLT:
                item.remarks = (item.remarks + " [Reconciled: quantity exceeds computed flange joints]").strip()

    # 4. Recomputes MTO Summary
    total_pipe_length = sum(item.length_m for item in validated_items if item.category == ItemCategory.PIPE and item.length_m)
    fittings_cnt = sum(int(item.quantity) for item in validated_items if item.category == ItemCategory.FITTING)
    flanges_cnt = sum(int(item.quantity) for item in validated_items if item.category == ItemCategory.FLANGE)
    valves_cnt = sum(int(item.quantity) for item in validated_items if item.category == ItemCategory.VALVE)
    gaskets_cnt = sum(int(item.quantity) for item in validated_items if item.category == ItemCategory.GASKET)
    bolts_cnt = sum(int(item.quantity) for item in validated_items if item.category == ItemCategory.BOLT)
    welds_cnt = sum(int(item.quantity) for item in validated_items if item.category == ItemCategory.WELD)
    supports_cnt = sum(int(item.quantity) for item in validated_items if item.category == ItemCategory.SUPPORT)

    # Recompute summary
    summary = MTOSummary(
        total_pipe_length_m=round(total_pipe_length, 2),
        fittings=fittings_cnt,
        flanges=flanges_cnt,
        valves=valves_cnt,
        gaskets=gaskets_cnt,
        bolt_sets=bolts_cnt,
        field_welds=welds_cnt,
        supports=supports_cnt
    )

    # Discrepancy warning detection:
    # If the LLM returned a summary object and it had total_pipe_length_m, check it.
    raw_summary = raw_data.get("summary", {})
    if isinstance(raw_summary, dict) and "total_pipe_length_m" in raw_summary:
        try:
            raw_len = float(raw_summary.get("total_pipe_length_m") or 0)
            if raw_len > 0 and abs(raw_len - total_pipe_length) / raw_len > 0.05:
                # Add warning remark to pipe items
                for item in validated_items:
                    if item.category == ItemCategory.PIPE:
                        item.remarks = (item.remarks + f" [QA warning: LLM reported {raw_len} m, computed {round(total_pipe_length, 2)} m]").strip()
        except Exception:
            pass

    # 5. Sequential item re-numbering
    for idx, item in enumerate(validated_items):
        item.item_no = idx + 1

    return MTOResponse(
        job_id=job_id,
        status=JobStatus.COMPLETED,
        source="mock",  # This will be overwritten by route handler with actual extractor source
        drawing_meta=drawing_meta,
        items=validated_items,
        summary=summary
    )
