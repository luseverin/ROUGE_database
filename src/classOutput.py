## Define class outputs to format LLM outputs
from pydantic import BaseModel, model_validator, RootModel
from typing import List, Optional, Literal
from src.hazard_def import hazard_subtype_kw_searc
from src.impact_def import impact_subtypes_desc_dict

hazardTypes_list = ["drought", "wildfire", "forest fire", "land fire", "ground movement", "tsunami", "avalanche", "landslide", "rockfall", "sudden subsidence", "mudslide", "ash fall", "lava flow", "pyroclastic flow", "lahar", "coastal flood", "flash flood", "riverine flood", "ice jam flood", "rogue wave", "seiche", "coldwave", "heatwave", "severe winter conditions", "derecho", "hail", "lightning", "winterstorm", "storm surge", "tornado", "extra-tropical storm", "tropical storm" ]
impactTypes_list = impact_subtypes_desc_dict.keys()
class ImpactDetail(BaseModel):
    impactType: Literal[tuple(impactTypes_list)]  # Accepts only values from impactTypes_list
    impactValue: Optional[int] = None
    impactUnit: Optional[str] = None
    impactValueFlag : Optional[str] = None
    location : List[str]
    startYear : Optional[int] = None
    startMonth : Optional[int] = None
    startDay : Optional[int] = None
    endYear : Optional[int] = None
    endMonth : Optional[int] = None
    endDay : Optional[int] = None
    hazards : List[Literal[tuple(hazardTypes_list)]]
    impactsAnnotation : List[str]

    #the following should work with output directly as a list
    @model_validator(mode="before")
    def validate_fields(cls, values):
        if "impactType" in values and values["impactType"] not in impactTypes_list:
            raise ValueError(f"Invalid impactType: {values['impactType']}")
        if "hazards" in values:
            invalid_hazards = [
                hazard for hazard in values["hazards"] if hazard not in hazardTypes_list
            ]
            if invalid_hazards:
                raise ValueError(f"Invalid hazards: {invalid_hazards}")
        return values

#the following expects a dict with "impacts as a key"
#class ImpactList(BaseModel):
#    impacts: List[ImpactDetail]

class ImpactList(BaseModel):
    RootModel: List[ImpactDetail]

