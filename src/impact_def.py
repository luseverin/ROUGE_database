#Constants for impact definition
from src.ImpactRegistry import Impacts
#define each impact

Impacts.register(
    key="Affected People",
    main_type="Human",
    description="Total number of individuals impacted by the hazard event.",
    keyword=r"\bAffected People\b",
    expected_unit="people",
    default_unit="people"
)

Impacts.register(
    key="Injured People",
    main_type="Human",
    description="Number of people injured, including those hospitalised or admitted.",
    keyword=r"\bInjured People\b",
    expected_unit="injuries",
    default_unit="people"
)

Impacts.register(
    key="Displaced People",
    main_type="Human",
    description="Number of people forcefully displaced or evacuated before or following the event.",
    keyword=r"\b(Displaced People|Displacement)\b",
    expected_unit="displaced",
    default_unit="people"
)

Impacts.register(
    key="Homeless People",
    main_type="Human",
    description="Number of people losing housing following the event.",
    keyword=r"\bHomeless People\b",
    expected_unit="homelesses",
    default_unit="people"
)

Impacts.register(
    key="Missing People",
    main_type="Human",
    description="Number of people unaccounted for following the event.",
    keyword=r"\bMissing People\b",
    expected_unit="missings",
    default_unit="people"
)

Impacts.register(
    key="Human Deaths",
    main_type="Human",
    description="Number of fatalities caused by the hazard.",
    keyword=r"\bHuman Deaths\b",
    expected_unit="deaths",
    default_unit="people"
)

Impacts.register(
    key="Infected and Ill People",
    main_type="Human",
    description="Number of people contaminated (cases) by an infectious disease.",
    keyword=r"\bInfected and Ill People\b",
    expected_unit="cases",
    default_unit="people"
)

Impacts.register(
    key="Human Health and Wellbeing",
    main_type="Human",
    description="Generic impacts on human health (physical, mental) or wellbeing not directly associated with the spread of an infectious disease.",
    keyword=r"\bHuman Health and Wellbeing\b",
    expected_unit="unknown",
    default_unit="unknown"
)

Impacts.register(
    key="Road Infrastructure",
    main_type="Infrastructure",
    description="Roads and road infrastructure (e.g. bridges, highways..) impacted by a hazard.",
    keyword=r"\b(Road Infrastructure|road)s?\b",
    expected_unit="roads",
    default_unit="roads"
)

Impacts.register(
    key="Other Transportation Infrastructure",
    main_type="Infrastructure",
    description="Transportation infrastructure, other than roads, impacted by a hazard. For example: Railways, airport, ferries, cars…",
    keyword=r"\bOther Transportation Infrastructure\b",
    expected_unit="transportation structures",
    default_unit="undefined transportation structures"
)

Impacts.register(
    key="Water, Sanitation, and Hygiene Infrastructure",
    main_type="Infrastructure",
    description="Number of water, sanitation, and hygiene infrastructure such as sewage networks, drainage systems, wastewater treatment plants, etc. impacted by a hazard.",
    keyword=r"\bWater,?\s*Sanitation,?\s*and Hygiene Infrastructure\b",
    expected_unit="WASH structures",
    default_unit="undefined WASH structures"
)

Impacts.register(
    key="Healthcare Infrastructure",
    main_type="Infrastructure",
    description="Number of healthcare infrastructure such as hospitals, healthcare centers, pharmacies, clinics, etc. impacted by a hazard.",
    keyword=r"\bHealthcare Infrastructure\b",
    expected_unit="healthcare structures",
    default_unit="undefined healthcare structures"
)

Impacts.register(
    key="IT and Communication Infrastructure",
    main_type="Infrastructure",
    description="Number of IT and communication infrastructure such as data centers, communication towers, and cables impacted by a hazard.",
    keyword=r"\bIT and Communication Infrastructure\b",
    expected_unit="IT and communication structures",
    default_unit="undefined IT and communication structures"
)

Impacts.register(
    key="Residential Buildings",
    main_type="Infrastructure",
    description="Number of residential buildings impacted by a hazard. This category also encompasses the impact on houses.",
    keyword=r"\bResidential Buildings\b",
    expected_unit="homes",
    default_unit="homes"
)

Impacts.register(
    key="Informal Settlements",
    main_type="Infrastructure",
    description="Number of informal settlements such as refugee camps, slums, tents, etc. impacted by a hazard.",
    keyword=r"\bInformal settlements\b",
    expected_unit="informal settlements",
    default_unit="informal settlements"
)

Impacts.register(
    key="Education Infrastructure",
    main_type="Infrastructure",
    description="Number of education infrastructures such as schools, universities, etc. impacted by a hazard.",
    keyword=r"\bEducation Infrastructure\b",
    expected_unit="education structures",
    default_unit="education structures"
)

Impacts.register(
    key="Power and Energy Production Infrastructure",
    main_type="Infrastructure",
    description="Number of energy production infrastructures such as power plants, turbines, grids, pipelines, etc., impacted by a hazard.",
    keyword=r"\bPower and Energy Production Infrastructure\b",
    expected_unit="power and energy production structures",
    default_unit="undefined power and energy production structures"
)

#Impacts.register(
#    key="Agricultural Infrastructure",
#    main_type="Infrastructure",
#    description="Number of agricultural infrastructures such as farms, warehouses, greenhouses, etc. impacted by a hazard. This category should also gather impacted infrastructure for fisheries such as vessels, boats, etc.",
#    keyword=r"\bAgricultur(?:e|al)? Infras(?:tructure|tucture)\b",
#    expected_unit="agricultural structures",
#    default_unit="undefined agricultural structures"
#)

Impacts.register(
    key="Crop Production and Forestry",
    main_type="Agriculture",
    description="Number of crops, agricultural production and forest impacted by a hazard.",
    keyword=r"\b(Crop Production and Forestry|Other Agricultural Impacts?|Agriculture|Other Agriculture Impacts?|Agricultural Infrastructure)\b",
    expected_unit="crop production and forestry",
    default_unit="crop production and forestry"
)

Impacts.register(
    key="Affected Livestock and Animals",
    main_type="Agriculture",
    description="Total number of animals, including terrestrial and aquatic species, impacted by the hazard (e.g. loss, death, perished animals or fishes).",
    keyword=r"\bAffected Livestock and Animals\b",
    expected_unit="affected animals",
    default_unit="affected animals"
)

Impacts.register(
    key="Recreation, Tourism, and Culture",
    main_type="Economy and Culture",
    description="Tourist attractions and cultural sites impacted by a hazard.",
    keyword=r"\bRecreation, Tourism, and Culture\b",
    expected_unit="unknown",
    default_unit="unknown"
)

Impacts.register(
    key="Economy and Livelihood",
    main_type="Economy and Culture",
    description="Any identified impact on the economy or living conditions resulting from a natural hazard.",
    keyword=r"\b(Other Economic(?: Activity)? (?:and|&) Livelihood (?:Production|Impact(?:s)?)|Economy and Market|Livelihood|employment|basic needs)\s*\b",
    expected_unit="businesses",
    default_unit="unknown"
)

Impacts.register(
    key="Access to Healthcare",
    main_type="Service access",
    description="People losing the ability to obtain needed medical services, including preventative care, emergency services…",
    keyword=r"\bAccess to Healthcare\b",
    expected_unit="people",
    default_unit="people"
)

Impacts.register(
    key="Access to Food",
    main_type="Service access",
    description="People losing access to a secure food supply.",
    keyword=r"\bfood\b",
    expected_unit="people",
    default_unit="people"
)

Impacts.register(
    key="Mobility and Access to Transport",
    main_type="Service access",
    description="People losing the capacity to move safely and efficiently between locations.",
    keyword=r"\b(Access to transport and Mobility|Access to transport|Mobility)\b",
    expected_unit="people",
    default_unit="people"
)

Impacts.register(
    key="Access to Water, Sanitation, and Hygiene",
    main_type="Service access",
    description="People losing access to water, sanitation, and hygiene services.",
    keyword=r"\bAccess to Water,?\s*Sanitation,?\s*and Hygiene\b",
    expected_unit="people",
    default_unit="people"
)

Impacts.register(
    key="Water Quality and Availability",
    main_type="Service access",
    description="People losing safe, clean, and consistent supply of water for drinking, sanitation, and other essential uses.",
    keyword=r"\bWater Quality and Availability\b",
    expected_unit="water points",
    default_unit="unknown"
)

Impacts.register(
    key="Access to Education",
    main_type="Service access",
    description="People losing the ability to attend educational institutions and receive instruction.",
    keyword=r"\bAccess to Education\b",
    expected_unit="people",
    default_unit="people"
)

Impacts.register(
    key="Access to Power and Energy",
    main_type="Service access",
    description="People losing access to electricity, gas, or other energy sources necessary for households, businesses, and public services.",
    keyword=r"\bAccess to Power and Energy\b",
    expected_unit="people",
    default_unit="people"
)

#Impacts.register(
#    key="Other Human Impacts",
#    main_type="Human",
#    description="Any identified impact on humans which cannot be associated with the previous impactSubtypes.",
#    keyword=r"\bOther Human.* Impacts?\b",
#    expected_unit="unknown",
#    default_unit="unknown"
#)
#Impacts.register(
#    key="Other Infrastructural Impacts",
#    main_type="Infrastructure",
#    description="Any identified impact on infrastructure which cannot be associated with the previous impactSubtypes, e.g. dykes, embankment, shops, etc.",
#    keyword=r"\b(Other Infrastructur(?:e|al)? Impacts?)\b",
#    expected_unit="undefined structures",
#    default_unit="unknown"
#)
Impacts.register(
    key="Undefined Infrastructure",
    main_type="Infrastructure",
    description="Any identified impact on infrastructure where the type of infrastructure impacted is not clearly defined, e.g. critical infrastructure, public infrastructure, etc.",
    keyword=r"\b(Undefined Infrastructure|Other Infrastructur(al|e) impacts?)\b",
    expected_unit="undefined structures",
    default_unit="unknown"
)
#Impacts.register(
#    key="Other Service Access Impacts",
#    main_type="Service access",
#    description="Any identified impact on service access which cannot be associated with the previous impactSubtypes.",
#    keyword=r"\bOther Service Access(?: Impacts?)?\b",
#    expected_unit="people",
#    default_unit="people"
Impacts.register(
    key="Undefined Service Access",
    main_type="Service access",
    description="Any identified impact on service access where the type of service impacted is not clearly defined, e.g. access to basic services",
    keyword=r"\b(Undefined Service Access|Other Service Access(?: Impacts?)?)\b",
    expected_unit="people",
    default_unit="people"
)

#Impacts.register(
#    key="Other Agricultural Impacts",
#    main_type="Agriculture",
#    description="Any identified impact on agriculture which cannot be associated with the previous impactSubtypes.",
#    keyword=r"\bOther Agricultural.* Impacts?\b",
#    expected_unit="unknown",
#    default_unit="unknown"
#)

Impacts.register(
    key="DREF Allocation",
    main_type="Economy and Culture",
    description="The DREF allocation for the event in CHF or other currency.",
    keyword=r"\bDREF Allocation\b",
    expected_unit=None,#"CHF", ! None to avoid automatic conversion
    default_unit="CHF"
)

Impacts.register(
    key="Targeted People",
    main_type="Human",
    description="The number of people targeted by recovery or response measures after the event.",
    keyword=r"\bTargeted people\b",
    expected_unit="people",
    default_unit="people"

)

Impacts.register(
    key="Assisted People",
    main_type="Human",
    description="The number of people assisted by recovery or response measures after the event.",
    keyword=r"\bAssisted People\b",
    expected_unit="people",
    default_unit="people"
)

IMPACT_TYPES = Impacts.get_main_types()
IMPACT_SUBTYPES = Impacts.get_subtypes()
IMPACT_DESCRIPTIONS = Impacts.get_descriptions()
IMPACT_KEYWORDS = Impacts.get_keywords()
IMPACT_EXPECTED_UNITS = Impacts.get_expected_units()
IMPACT_DEFAULT_UNITS = Impacts.get_default_units()

IMPACT_SUBTYPE_MERGER = {
    "Transportation" : r"(Road Infrastructure|Other Transportation Infrastructure|Mobility and Access to Transport)",
    "Water, Sanitation, and Hygiene" : r"(Water, Sanitation, and Hygiene Infrastructure|Access to Water, Sanitation, and Hygiene|Water Quality and Availability)",
    "Healthcare" : r"(Healthcare Infrastructure|Access to Healthcare)",
    "IT and Communication" : r"(IT and Communication Infrastructure|Access to IT and Communication Infrastructure)",
    "Education" : r"(Education Infrastructure|Access to Education)",
    "Agriculture and Access to Food" : r"(Agricultural Infrastructure|Access to Food|Crop Production and Forestry|Affected Livestock and Animals|Other Agricultural Impacts)",
    "Power and Energy Production" : r"(Power and Energy Production Infrastructure|Access to Power and Energy)",
    "Undefined Infrastructure and Service Access" : r"(Undefined Infrastructure|Undefined Service Access|Other Service Access (Impacts)?|Other Infrastructural Impacts)",
}
IMPACT_SUBTYPES_MERGED = [el for el in IMPACT_SUBTYPES if el not in ["Road Infrastructure",
                                                                     "Other Transportation Infrastructure",
                                                                     "Mobility and Access to Transport",
                                                                     "Water, Sanitation, and Hygiene Infrastructure",
                                                                     "Access to Water, Sanitation, and Hygiene",
                                                                     "Water Quality and Availability",
                                                                     "Healthcare Infrastructure",
                                                                     "Access to Healthcare",
                                                                     "IT and Communication Infrastructure",
                                                                     "Access to IT and Communication Infrastructure",
                                                                     "Education Infrastructure",
                                                                     "Access to Education",
                                                                     "Agricultural Infrastructure",
                                                                     "Access to Food",
                                                                     "Crop Production and Forestry",
                                                                     "Affected Livestock and Animals",
                                                                     "Other Agricultural Impacts",
                                                                     "Power and Energy Production Infrastructure",
                                                                     "Access to Power and Energy",
                                                                     "Undefined Infrastructure",
                                                                     "Undefined Service Access"
                                                                     ]]

IMPACT_SUBTYPES_MERGED += [k for k in IMPACT_SUBTYPE_MERGER.keys()]

# Update impact main type
IMPACT_TYPES_MERGER = {"Transportation" : "Infrastructure and Service access",
                       "Water, Sanitation, and Hygiene" : "Infrastructure and Service access",
                       "Healthcare" : "Infrastructure and Service access",
                       "IT and Communication" : "Infrastructure and Service access",
                       "Education" : "Infrastructure and Service access",
                       "Agriculture and Access to Food" : "Infrastructure and Service access",
                       "Power and Energy Production" : "Infrastructure and Service access",
                       "Undefined Infrastructure and Service Access" : "Infrastructure and Service access"}

IMPACT_TYPES_MERGED = {}
for subtype in IMPACT_SUBTYPES_MERGED:
    main_type = IMPACT_TYPES.get(subtype, None)  # get main type only for this subtype
    if main_type in ["Infrastructure", "Service access"]:
        main_type = "Infrastructure and Service access"
    elif subtype in IMPACT_TYPES_MERGER.keys() :
        main_type = IMPACT_TYPES_MERGER[subtype]
    IMPACT_TYPES_MERGED[subtype] = main_type