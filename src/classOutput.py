from pydantic import BaseModel, ValidationError, field_validator, RootModel
from typing import List, Optional, Union

class ImpactSubtypes(BaseModel):
    impactSubtypes: List[str]
    # Dynamic constraints
    _impactSubtypes_list: List[str]

    @classmethod
    def set_allowed_subtypes(cls, impact_subtypes: List[str]):
        cls._impactSubtypes_list = impact_subtypes

    @field_validator("impactSubtypes")
    def validate_impact_subtype(cls, value):
        if not isinstance(value, list):# or isinstance(value, type(None)):
            raise ValueError(f"Expected a list or NoneType for impactSubtypes, got {type(value).__name__}")
        invalid_types = [subtypes for subtypes in value if subtypes not in cls._impactSubtypes_list]
        if invalid_types:
            raise ValueError(f"Invalid impactSubtypes: {invalid_types}. Must be one or more of {cls._impactSubtypes_list}")
        return value

class ImpactValue(BaseModel):
    impactSubtype: str
    impactValue: Optional[float] = None
    impactValueMin: Optional[float] = None
    impactValueMax: Optional[float] = None
    impactValuePrecision: Optional[str] = None
    impactUnit: Optional[str] = None
    valueAnnotation: List[str]

    _impactSubtypes_list: List[str]

    #marker to do impactSubtypes validation or not
    _validate_impactSubtypes = True

    @classmethod
    def turn_off_impactSubtypes_validation(cls):
        cls._validate_impactSubtypes = False

    @classmethod
    def set_allowed_subtypes(cls, impact_subtypes: List[str]):
        cls._impactSubtypes_list = impact_subtypes

    @field_validator("impactSubtype")
    def validate_impact_subtype(cls, value):
        if value not in cls._impactSubtypes_list:
            if cls._validate_impactSubtypes:
                raise ValueError(f"Invalid impactSubtype: {value}. Must be one of {cls._impactSubtypes_list}")
            else:
                print(f"Invalid impactSubtype: {value}. Must be one of {cls._impactSubtypes_list}")
        return value


class ImpactLocation(BaseModel):
    country: List[str]
    location: Optional[List[str]] = None
    locationAnnotation: List[str]

class ImpactDates(BaseModel):
    startYear: Optional[int] = None
    startMonth: Optional[int] = None
    startDay: Optional[int] = None
    endYear: Optional[int] = None
    endMonth: Optional[int] = None
    endDay: Optional[int] = None
    dateAnnotation: List[str]

class ImpactHazards(BaseModel):
    hazards: Optional[List[str]] = None
    hazardsAnnotation: List[str]

    _hazardTypes_list: Optional[List[str]] = None

    #marker to do hazard validation or not
    _validate_hazards = True

    @classmethod
    def turn_off_hazard_validation(cls):
        cls._validate_hazards = False

    @classmethod
    def set_allowed_classes(cls, hazard_types: Union[None, List[str]]):
        cls._hazardTypes_list = hazard_types

    @field_validator("hazards", mode="before")
    def validate_hazards(cls, value):
        if not isinstance(value, list):
            raise ValueError(f"Expected a list for hazards, got {type(value).__name__}")
        invalid_hazards = [hazard for hazard in value if hazard not in cls._hazardTypes_list]
        if invalid_hazards:
            if cls._validate_hazards:
                raise ValueError(f"Invalid hazards: {invalid_hazards}. Must be one of {cls._hazardTypes_list}")
            else:
                print(f"Invalid hazards: {invalid_hazards}. Must be one of {cls._hazardTypes_list}")
        return value
class ImpactDetail(ImpactValue, ImpactLocation, ImpactDates, ImpactHazards):
    pass

class ImpactDetailTypeSubType(ImpactDetail):
    impactType: str

    # Dynamic constraints
    _impactTypes_list: Optional[List[str]] = None

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

class ImpactDetailConstUnit(ImpactDetail):
    impactUnitType: Optional[str] = None

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

class ImpactDetailRange(ImpactDetail):
    impactValueMin: Optional[float] = None
    impactValueMax: Optional[float] = None


class ImpactList(RootModel):
    root: List[ImpactDetail]

class ImpactValueList(RootModel):
    root: List[ImpactValue]

class ImpactListTypeSubType(RootModel):
    root: List[ImpactDetailTypeSubType]

class ImpactListConstUnit(RootModel):
    root: List[ImpactDetailConstUnit]

class ImpactListRange(RootModel):
    root: List[ImpactDetailRange]

