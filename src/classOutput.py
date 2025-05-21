## Define class outputs to format LLM outputs
from pydantic import BaseModel
from typing import List, Optional

class ImpactDetail(BaseModel):
    impactValue: int
    impactUnit: str
    location : List[str]
    startYear : int
    startMonth : int
    startDay : int
    endYear : int
    endMonth : int
    endDay : int
    hazards : List[str]
    impactAnnotation : List[str]

class ImpactList(BaseModel):
    impacts: List[ImpactDetail]
