from pydantic import BaseModel, ValidationError, field_validator, RootModel
from typing import List, Optional, Union


class ImpactDetail(BaseModel):
    impactType: str
    impactSubtype: str
    impactValue: Optional[float] = None
    impactUnit: Optional[str] = None
    #impactUnitType: Optional[str] = None
    impactValueFlag: Optional[str] = None
    location: Optional[List[str]] = None
    startYear: Optional[int] = None
    startMonth: Optional[int] = None
    startDay: Optional[int] = None
    endYear: Optional[int] = None
    endMonth: Optional[int] = None
    endDay: Optional[int] = None
    hazards: Optional[List[str]] = None
    impactsAnnotation: List[str] = None

    # Dynamic constraints
    _impactTypes_list: Optional[List[str]] = None
    _impactSubtypes_list: Optional[List[str]] = None
    _hazardTypes_list: Optional[List[str]] = None

    @classmethod
    def set_allowed_classes(cls, impact_types: List[str], impact_subtypes: List[str], hazard_types: Union[None, List[str]]):
        cls._impactTypes_list = impact_types
        cls._impactSubtypes_list = impact_subtypes
        cls._hazardTypes_list = hazard_types

    @field_validator("impactType")
    def validate_impact_type(cls, value):
        if value not in cls._impactTypes_list:
            raise ValueError(f"Invalid impactType: {value}. Must be one of {cls._impactTypes_list}")
        return value
    @field_validator("impactSubtype")
    def validate_impact_subtype(cls, value):
        if value not in cls._impactSubtypes_list:
            raise ValueError(f"Invalid impactSubtype: {value}. Must be one of {cls._impactSubtypes_list}")
        return value

    @field_validator("hazards", mode="before")
    def validate_hazards(cls, value):
        if not isinstance(value, list):
            raise ValueError(f"Expected a list for hazards, got {type(value).__name__}")
        invalid_hazards = [hazard for hazard in value if hazard not in cls._hazardTypes_list]
        if invalid_hazards:
            raise ValueError(f"Invalid hazards: {invalid_hazards}. Must be one of {cls._hazardTypes_list}")
        return value

class ImpactDetailConstUnit(ImpactDetail):
    # Dynamic constraints
    _impactUnits_list: Optional[List[str]] = None

    @classmethod
    def set_allowed_classes(cls, impact_types: List[str], impact_subtypes: List[str], impact_units: Union[None, List[str]], hazard_types: List[str]):
        cls._impactTypes_list = impact_types
        cls._impactSubtypes_list = impact_subtypes
        cls._impactUnits_list = impact_units
        cls._hazardTypes_list = hazard_types

    @field_validator("impactUnit")
    def validate_impact_unit(cls, value):
        if value and value not in cls._impactUnits_list:
            raise ValueError(f"Invalid impactUnit: {value}. Must be one of {cls._impactUnits_list}")
        return value

class ImpactList(RootModel):
    root: List[ImpactDetail]

class ImpactListConstUnit(RootModel):
    root: List[ImpactDetailConstUnit]

