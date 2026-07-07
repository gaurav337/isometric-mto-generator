from typing import Any
from app.services.extractor import VisionExtractor

class MockExtractor(VisionExtractor):
    @property
    def source(self) -> str:
        return "mock"

    def extract(self, image_b64: str) -> dict[str, Any]:
        """
        Returns a raw dictionary representing raw LLM output,
        containing DrawingMetadata fields and items list (excluding derived gaskets/bolts).
        """
        return {
            "drawing_meta": {
                "drawing_no": "ISO-1501-01",
                "revision": "2",
                "line_number": "6\"-P-1501-A1A-IH",
                "nps": "6\"",
                "material_class": "A1A",
                "service": "Process",
                "design_pressure": "1.6 MPa",
                "design_temperature": "120 C"
            },
            "items": [
                {
                    "item_no": 1,
                    "category": "PIPE",
                    "description": "Pipe, Seamless, BE, ASME B36.10",
                    "size_nps": "6\"",
                    "schedule_rating": "SCH 40",
                    "material_spec": "ASTM A106 Gr.B",
                    "end_type": "BW",
                    "quantity": 12.45,
                    "confidence": 0.95,
                    "remarks": "[MOCK DATA - no API key configured]"
                },
                {
                    "item_no": 2,
                    "category": "FITTING",
                    "description": "Elbow 90 Deg LR, BW, ASME B16.9",
                    "size_nps": "6\"",
                    "schedule_rating": "SCH 40",
                    "material_spec": "ASTM A234 WPB",
                    "end_type": "BW",
                    "quantity": 4,
                    "confidence": 0.92,
                    "remarks": "[MOCK DATA - no API key configured]"
                },
                {
                    "item_no": 3,
                    "category": "FITTING",
                    "description": "Equal Tee, BW, ASME B16.9",
                    "size_nps": "6\"",
                    "schedule_rating": "SCH 40",
                    "material_spec": "ASTM A234 WPB",
                    "end_type": "BW",
                    "quantity": 1,
                    "confidence": 0.90,
                    "remarks": "[MOCK DATA - no API key configured]"
                },
                {
                    "item_no": 4,
                    "category": "FLANGE",
                    "description": "Weld Neck Flange, WN, RF, CL150, ASME B16.5",
                    "size_nps": "6\"",
                    "schedule_rating": "SCH 40",
                    "material_spec": "ASTM A105",
                    "end_type": "BW",
                    "quantity": 2,
                    "confidence": 0.88,
                    "remarks": "[MOCK DATA - no API key configured]"
                },
                {
                    "item_no": 5,
                    "category": "VALVE",
                    "description": "Gate Valve, Flanged, CL150, Bowtie plain, ASME B16.34",
                    "size_nps": "6\"",
                    "schedule_rating": "CL150",
                    "material_spec": "ASTM A216 WCB",
                    "end_type": "FLGD",
                    "quantity": 1,
                    "confidence": 0.87,
                    "remarks": "[MOCK DATA - no API key configured]"
                },
                {
                    "item_no": 6,
                    "category": "SUPPORT",
                    "description": "Piping Support Shoe, CS, Type PS-01",
                    "size_nps": "6\"",
                    "schedule_rating": None,
                    "material_spec": "CS",
                    "end_type": None,
                    "quantity": 2,
                    "confidence": 0.80,
                    "remarks": "[MOCK DATA - no API key configured]"
                }
            ],
            # Recomputed summary to simulate what the model outputted
            "summary": {
                "total_pipe_length_m": 12.45,
                "fittings": 5,
                "flanges": 2,
                "valves": 1
            }
        }
