### Examples
examples_subtypes = """{
       "impactSubtypes" : ["Affected People", "Crop Production and Forestry", "Healthcare Infrastructure"]
       }"""
examples_value_unit = """[{
       "impactSubtype" : "Affected People",
       "impactValue": "10000",
       "impactUnit": "people",
       "impactValuePrecision" : "exact"
       "impactValueMin": null,
       "impactValueMax": null
       "valueAnnotation": ["Landslides impacted 10000 people in the cities of Abu Hamad and Tokar on the 29 August 2024"]
       },
       {
       "impactSubtype" : "Crop Production and Forestry",
       "impactValue":null,
       "impactUnit": "kg of crop production",
       "impactValuePrecision" : "approx",
       "impactValueMin": 100,
       "impactValueMax": 200,
       "valueAnnotation": ["Flash floods and tsunamis impacted 100 to 200 kg of crop production in Red Sea State between August to October 2024"]
       },
       {
       "impactSubtype" : "Healthcare Infrastructure",
       "impactValue": 4,
       "impactUnit": "healthcare facilities",
       "impactValuePrecision" : "approx",
       "impactValueMin": 4,
       "impactValueMax": null,
       "valueAnnotation": ["At least 4 hospitals have been impacted by a hailstorm in River Nile State alone."]
       }]"""

examples_location = """{
       "country" : ["Sudan"],
       "location" : ["Abu Hamad", "Tokar"]
       "locationAnnotation": ["Landslides impacted 10000 people in the cities of Abu Hamad and Tokar on the 29 August 2024"]
       }"""

examples_date = """{
       "startYear" : 2024,
       "startMonth" : 08,
       "startDay" : 29,
       "endYear" : null,
       "endMonth" : null,
       "endDay" : null,
       "dateAnnotation": ["Landslides impacted 10000 people in the cities of Abu Hamad and Tokar on the 29 August 2024"]
       }"""

example_hazards = """{
       "hazards" : ["Mass movement"]
       "hazardsAnnotation": ["Landslides impacted 10000 people in the cities of Abu Hamad and Tokar on the 29 August 2024"]
       }"""


examples_base = """[{
       "impactSubtype" : "Affected People",
       "impactValue": "10000",
       "impactUnit": "people",
       "impactValuePrecision" : "exact",
       "country" : "Sudan",
       "location" : ["Abu Hamad", "Tokar"],
       "startYear" :2024,
       "startMonth" :08,
       "startDay" : 29,
       "endYear" : null,
       "endMonth" : null,
       "endDay" : null,
       "hazards" : ["Mass movement"],
       "impactsAnnotation" : ["Landslides impacted 10000 people in the cities of Abu Hamad and Tokar on the 29 August 2024",]
      },
      {
       "impactSubtype" : "Crop Production and Forestry",
       "impactValue": "100 to 200",
       "impactUnit": "kg of crop production",
       "impactValuePrecision" : "approx",
       "country" : "Sudan",
       "location" : ["Red Sea State"],
       "startYear" : 2024,
       "startMonth" : 08,
       "startDay" : null,
       "endYear" : 2024,
       "endMonth" : 10,
       "endDay" : null,
       "hazards" : ["Flood"],
       "impactsAnnotation" : ["Flash floods impacted 100 to 200 kg of crop production in Red Sea State between August to October 2024"]
      },
      {
       "impactSubtype" : "Healthcare Infrastructure",
       "impactValue": "4",
       "impactUnit": "healthcare facilities",
       "impactValueFlag" : "approx",
       "country" : "Sudan",
       "location": ["River Nile State"],
       "startYear": null,
       "startMonth": null,
       "startDay": null,
       "endYear": null,
       "endMonth": null,
       "endDay": null,
       "hazards" : ["Convective storm"],
       "impactsAnnotation" : ["At least 4 hospitals have been impacted by a hailstorm in River Nile State alone."]
       }]
    """
examples_type_subtype = """[{
       "impactType" : "Human",
       "impactSubtype" : "Affected People",
       "impactValue": "10000",
       "impactUnit": "people",
       "impactValuePrecision" : "exact",
       "country" : "Sudan",
       "location" : ["Abu Hamad", "Tokar"],
       "startYear" :"2024,
       "startMonth" :"08,
       "startDay" : 29,
       "endYear" : null,
       "endMonth" : null,
       "endDay" : null,
       "hazards" : ["Mass movement"],
       "impactsAnnotation" : ["Landslides impacted 10000 people in the cities of Abu Hamad and Tokar on the 29 August 2024",]
      },
      {
       "impactType" : "Agriculture",
       "impactSubtype" : "Crop Production and Forestry",
       "impactValue": "100 to 200",
       "impactUnit": "kg of crop production",
       "impactValuePrecision" : "approx",
       "country" : "Sudan",
       "location" : ["Red Sea State"],
       "startYear" : 2024,
       "startMonth" : 08,
       "startDay" : null,
       "endYear" : 2024,
       "endMonth" : 10,
       "endDay" : null,
       "hazards" : ["Flood"],
       "impactsAnnotation" : ["Flash floods impacted 100 to 200 kg of crop production in Red Sea State between August to October 2024"]
      },
      {
       "impactType" : "Infrastructure",
       "impactSubtype" : "Healthcare Infrastructure",
       "impactValue": "4",
       "impactUnit": "healthcare facilities",
       "impactValuePrecision" : "approx",
       "country" : "Sudan",
       "location": ["River Nile State"],
       "startYear": null,
       "startMonth": null,
       "startDay": null,
       "endYear": null,
       "endMonth": null,
       "endDay": null,
       "hazards" : ["Convective storm"],
       "impactsAnnotation" : ["At least 4 hospitals have been impacted by a hailstorm in River Nile State alone."]
       }]
    """
examples_range = """[{
       "impactSubtype" : "Affected People",
       "impactValue": 10000,
       "impactValuePrecision" : "exact",
       "impactValueMin" : 10000,
       "impactValueMax" : 10000,
       "impactUnit": "people",
       "country" : ["Sudan"],
       "location" : ["Abu Hamad", "Tokar"],
       "startYear" :2024,
       "startMonth" :08,
       "startDay" : 29,
       "endYear" : null,
       "endMonth" : null,
       "endDay" : null,
       "hazards" : ["Mass movement"],
       "impactsAnnotation" : ["Landslides impacted 10000 people in the cities of Abu Hamad and Tokar on the 29 August 2024",]
      },
      {
       "impactSubtype" : "Crop Production and Forestry",
       "impactValue": 200,
       "impactValuePrecision" : "approx",
       "impactValueMin" : 100,
       "impactValueMax" : 200,
       "impactUnit": "kg of crop production",
       "country" : ["Sudan"],
       "location" : ["Red Sea State"],
       "startYear" : 2024,
       "startMonth" : 08,
       "startDay" : null,
       "endYear" : 2024,
       "endMonth" : 10,
       "endDay" : null,
       "hazards" : ["Flood", "Earthquake"],
       "impactsAnnotation" : ["Flash floods and tsunamis impacted 100 to 200 kg of crop production in Red Sea State between August to October 2024"]
      },
      {
       "impactSubtype" : "Healthcare Infrastructure",
       "impactValue": 4,
       "impactValuePrecision" : "approx",
       "impactValueMin" : 4,
       "impactValueMax" : 4,
       "impactUnit": "healthcare facilities",
       "country" : ["Sudan"],
       "location": ["River Nile State"],
       "startYear": null,
       "startMonth": null,
       "startDay": null,
       "endYear": null,
       "endMonth": null,
       "endDay": null,
       "hazards" : ["Convective storm"],
       "impactsAnnotation" : ["At least 4 hospitals have been impacted by a hailstorm in River Nile State alone."]
       }]
    """
examples_groq = """
Input:
## DREF Operational Report ##
OPERATION IFRC N1213. FUNDING: 13413413 CHF.
Landslides impacted 10000 people in the cities of Abu Hamad and Tokar on the 29 August 2024.
Flash floods and tsunamis impacted 100 to 200 kg of crop production in Red Sea State between August to October 2024
At least 4 hospitals have been impacted by a hailstorm in River Nile State alone.
Recovery operations include: restoration of infrastructure and infrastructure maintenance.

Output:
{
   "impactSubtype" : "Affected People",
   "impactValue": 10000,
   "impactValuePrecision" : "exact",
   "impactValueMin" : 10000,
   "impactValueMax" : 10000,
   "impactUnit": "people",
   "country" : ["Sudan"],
   "location" : ["Abu Hamad", "Tokar"],
   "startYear" :2024,
   "startMonth" :08,
   "startDay" : 29,
   "endYear" : null,
   "endMonth" : null,
   "endDay" : null,
   "hazards" : ["Mass movement"],
   "impactsAnnotation" : ["Landslides impacted 10000 people in the cities of Abu Hamad and Tokar on the 29 August 2024",]
},
{
 "impactSubtype" : "Crop Production and Forestry",
 "impactValue": 200,
 "impactValuePrecision" : "approx",
 "impactValueMin" : 100,
 "impactValueMax" : 200,
 "impactUnit": "kg of crop production",
 "country" : ["Sudan"],
 "location" : ["Red Sea State"],
 "startYear" : 2024,
 "startMonth" : 08,
 "startDay" : null,
 "endYear" : 2024,
 "endMonth" : 10,
 "endDay" : null,
 "hazards" : ["Flood", "Earthquake"],
 "impactsAnnotation" : ["Flash floods and tsunamis impacted 100 to 200 kg of crop production in Red Sea State between August to October 2024"]
},
{
 "impactSubtype" : "Healthcare Infrastructure",
 "impactValue": 4,
 "impactValuePrecision" : "approx",
 "impactValueMin" : 4,
 "impactValueMax" : 4,
 "impactUnit": "healthcare facilities",
 "country" : ["Sudan"],
 "location": ["River Nile State"],
 "startYear": null,
 "startMonth": null,
 "startDay": null,
 "endYear": null,
 "endMonth": null,
 "endDay": null,
 "hazards" : ["Convective storm"],
 "impactsAnnotation" : ["At least 4 hospitals have been impacted by a hailstorm in River Nile State alone."]
 }
"""