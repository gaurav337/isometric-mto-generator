from datetime import datetime, timezone
from enum import Enum
import re
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

class ItemCategory(str, Enum):
    PIPE = "PIPE"
    FITTING = "FITTING"
    FLANGE = "FLANGE"
    VALVE = "VALVE"
    GASKET = "GASKET"
    BOLT = "BOLT"
    SUPPORT = "SUPPORT"
    WELD = "WELD"

class ItemUnit(str, Enum):
    M = "M"      # metres — PIPE only
    EA = "EA"    # each — fittings, flanges, valves, supports, welds
    SET = "SET"  # set — BOLT

class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class DrawingMetadata(BaseModel):
    drawing_no: str = Field(..., description="Drawing Number")
    revision: str = Field(..., description="Revision Number")
    line_number: str = Field(..., description="Line Number, e.g., 6\"-P-1501-A1A-IH")
    nps: str = Field(..., description="Nominal Pipe Size, e.g., 6\"")
    material_class: str = Field(..., description="Piping Material Class, e.g., A1A")
    service: str = Field(..., description="Service abbreviation / description, e.g., Process")
    design_pressure: str | None = None
    design_temperature: str | None = None

class MTOItem(BaseModel):
    item_no: int = Field(..., description="Sequential item index")
    category: ItemCategory = Field(..., description="Piping material category")
    description: str = Field(..., description="ASME/ASTM specification description")
    size_nps: str = Field(..., description="Nominal size in inches (supports reducing formats like 6\"x4\")")
    schedule_rating: str | None = Field(None, description="Wall thickness schedule or rating class")
    material_spec: str | None = Field(None, description="ASTM/ASME material grade")
    end_type: str | None = Field(None, description="End connection (BW, SW, THD, FLGD)")
    quantity: float = Field(..., description="Quantity count or pipe length")
    unit: ItemUnit = Field(..., description="Unit of measurement")
    length_m: float | None = Field(None, description="Total cut length (PIPE category only)")
    segment_lengths: list[float] | None = Field(None, description="List of individual pipe segment lengths (PIPE category only)")
    confidence: float | None = Field(None, ge=0.0, le=1.0, description="Confidence score")
    remarks: str = Field("", description="Remarks or special notes")

    @field_validator("size_nps")
    @classmethod
    def validate_size_nps(cls, v: str) -> str:
        # Normalize: strip whitespace and check format: e.g., 6", 6"x4", 1/2", 1.5", 1-1/2", etc.
        # Standardize X/x to lowercase x
        cleaned = v.strip().replace("X", "x")
        pattern = r'^(\d+(?:[./-]\d+)?)"(?:x(\d+(?:[./-]\d+)?)"|x(\d+))?$'
        if not re.match(pattern, cleaned):
            flexible_pattern = r'^\d+(\.\d+)?/?\d*"(x\d+(\.\d+)?/?\d*")?$'
            if not re.match(flexible_pattern, cleaned):
                if '"' not in cleaned:
                    raise ValueError("NPS size must contain double quotes (\") to denote inches")
        return cleaned

    @model_validator(mode="after")
    def validate_length_m_for_pipe(self) -> "MTOItem":
        if self.category == ItemCategory.PIPE:
            if self.length_m is None or self.length_m <= 0:
                # If quantity is provided, we can use it as length_m.
                if self.quantity > 0:
                    self.length_m = self.quantity
                else:
                    raise ValueError("PIPE items must have a positive length_m or quantity")
            # Enforce unit is M for pipes
            self.unit = ItemUnit.M
        else:
            self.length_m = None
            if self.category == ItemCategory.BOLT:
                self.unit = ItemUnit.SET
            else:
                self.unit = ItemUnit.EA
        return self

class MTOSummary(BaseModel):
    total_pipe_length_m: float = Field(0.0, description="Summed pipe length in meters")
    fittings: int = Field(0, description="Fitting count")
    flanges: int = Field(0, description="Flange count")
    valves: int = Field(0, description="Valve count")
    gaskets: int = Field(0, description="Gasket count")
    bolt_sets: int = Field(0, description="Bolt sets count")
    field_welds: int = Field(0, description="Field welds count")
    supports: int = Field(0, description="Supports count")

class MTOResponse(BaseModel):
    job_id: str
    status: JobStatus
    source: Literal["nvidia", "gemini", "openrouter", "mock"]
    image_b64: str | None = None
    drawing_meta: DrawingMetadata | None = None
    items: list[MTOItem] = []
    summary: MTOSummary | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

class UploadResponse(BaseModel):
    job_id: str
    status: JobStatus

class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None

