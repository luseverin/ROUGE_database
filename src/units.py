# Define unit conversion mapping
DEF_CUR = "EUR"
METRIC_UNIT_MAPPING = {
    "km": "km",
    "km**2": "km**2",
    "miles": "km",
    "kg": "kg",
    "m**3": "m**3",
    "acre": "km**2",
    "feet": "km",
    "meter": "km",
    "hectare": "km**2",
    "ha": "km**2",
    "mi**2": "km**2",
    "m**2": "km**2",
    "ft**2": "km**2",
    "pound": "kg",
    "ton": "kg",
    "tonne": "kg",
    "liter": "m**3",
    "l": "m**3",
    "gallon": "m**3",
}
METRIC_UNIT_KW_RECLASS = {
    "km": [
        r"(?<!\b(squared?)\b)\s\b(kilometers?|kilometres?|kms?)\b(?!\s*(\*\*\s*2|\^2|²|squared?|2)\b)"
    ],
    "km**2": [
        r"\b(squared?)\s+(kilometers?|kilometres?|kms?)\b",
        r"\b(kilometers?|kilometres?|kms?)\s?(\*\*\s*2|\*\*2|\^2|²|squared?|2)\b(?<!\.\d)",
    ],
    "m**2": [
        r"\b(squared?)\s+(meters?|metres?|m)\b",
        r"\b(meters?|metres?|m)\s?(\*\*\s*2|\*\*2|\^2|²|square|squared|2)\b(?<!\.\d)",
    ],
    "mi**2": [
        r"\b(squared?)\s+(mile|miles|mi)\b",
        r"\b(mile|miles|mi)\s?(\*\*\s*2|\*\*2|\^2|²|squared?|2)\b(?<!\.\d)",
    ],
    "ft**2": [
        r"\b(squared?)\s+(feet|foot|ft)\b",
        r"\b(feet|foot|ft)\s?(\*\*\s*2|\*\*2|\^2|²|squared?|2)\b(?<!\.\d)",
    ],
    "kg": [r"\b(kgs?|kilograms?)\b"],
    "m**3": [
        r"\b(?<=(cube|cubic))\s*(meters?|metres?|m)\b",
        r"\b(meters?|metres?|m)s?\s?(\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3)\b(?<!\.\d)",
    ],
    "acre": [r"\b(acres?|acers?)\b"],
    "feet": [
        r"(?<!\b(squared?|cube|cubic)\s*)\b(feet|foot|ft)\b(?!\s*(\*\*\s*2|\^2|²|squared?|2|\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3)|\s+\d+(\.\d+)?)"
    ],
    "hectare": [r"\b(hectares?|ha|hectors?)\b"],
    "ton": [r"\b(?<!\b(metric|mt)\s*)(ton|tons)\b"],
    "tonne": [r"\b(tonne|tonnes|metric tons?|mt)\b"],
    "pound": [r"\b(pounds|lbs?)\b"],
    "meter": [
        r"(?<!\b(squared?|cube|cubic)\s*)\b(meters?|metres?|m)\b(?!\s*(\*\*\s*2|\^2|²|squared?|2|\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3)|\s+\d+(\.\d+)?)"
    ],
    "liter": [r"\b(liters?|litres?|l)\b"],
    "miles": [
        r"(?<!\b(squared?|cube|cubic)\s*)\b(miles?|mi)\b(?!\s*(\*\*\s*2|\^2|²|squared?|2|\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3)|\s+\d+(\.\d+)?)"
    ],
    "gallon": [r"\b(gallons|gal)\b"],
}


# reclassify units
UNIT_CONVERTER = {
    r"\b(households)\b": (5, "people"),
    r"\b(villages)\b": (1000, "people"),
    r"\b(communities)\b": (100, "people"),
}

PEOPLE_NORMALIZER = r"\b(people|deaths|cases|injuries|displaced|missings|homelesses)\b"
UNIT_TYPE_KW_RECLASS = {
    "km": r"\b(?:kilometer|kilometre|km)s?(?!\s*(?:\*\*\s*2|\*\*2|\^2|²|square|squared|2))\b",
    "km**2": r"\b(?:kilometer|kilometre|km)s?\s*(?:\*\*\s*2|\*\*2|\^2|²|square|squared|2)\b",
    "kg": r"\b(kg|kilograms?)\b",
    "m**3": r"\b(?:meter|metre|m)s?\s?(?:\*\*\*\s*3|\*\*3|\^3|³|cube|cubic|3)\b",
    "%": r"\b(%|perc\.?|per(\s)?cent(s)?|percentages?)\b",
}
HARMONIZE_UNITS_KW = {
    "people": r"\b(people|persons?|individuals?|residents?)\b",
    "households": r"\b(family|families|households?|hhs?)\b",
    "communities": r"\b(community|communities)\b",
    "villages": r"\b(villages?|hamlets?)\b",
    "roads": r"\b(roads?|routes?|bridges?|highways?|motorways?)\b",
    "vehicles": r"\b(vehicles?|motor vehicles?|cars?|trucks?|vessels?|boats?)\b",
    "structures": r"\b(facilities|facility|buildings?|(infra)?structures?|buildings?|utilities?|institutions?)\b",
    "homes": r"\b(residences?|houses?|homes?|housing units?|dwellings?|properties?|housing structures?|residential structures?)\b",
    "%": r"\b(%|perc\.?|per(\s)?cent(s)?|percentages?)\b",
}

UNIT_KW_RECLASS = {
    #'people': r"\b(people)\b",
    "deaths": r"\b(fatalities?|deaths?|lives|loss(es)? of life|deceased|dead)\b",
    "displaced": r"\b(displaced|evacuees?|evacuated|idps?(?!\s*(sites?|camps?)))\b",
    "homelesses": r"\b(homeless(es)?|homeless people)\b",
    "injuries": r"\b(injuries|injured|injury|casualties|casualty)\b",
    "missings": r"\b(missing|missing persons?|missing individuals?|missing residents?|missing people|disappeared)\b",
    "cases": r"\b(cases?|cases of|cases of illness|infected)\b",
    "roads": r"\b(roads)\b",
    "transportation structures": r"\b(rail(way|road)?s?|train tracks?|airports?|vehicles?|seaports?)\b",
    "WASH structures": r"\b((water (points?|sources?|supply|supplies|systems))|wells?|taps?|reservoirs?|(sanitation|hygiene|wastewater) (structures|systems|treatment plants?)|water treatment plants?|latrines?|toilets?|aqueducts?|rainwater (collection|harvesting) systems?)\b",
    "healthcare structures": r"\b((health(care)?|medical) (centers?|centres?|units?|structures?)|hospitals?|clinics?|maternit(y|ies)|posts?)\b",
    "IT and communication structures": r"\b((tele)?communication(s)? (structures?|center?|lines?)|radios?|tv|cell towers?|antennas?)\b",
    "power and energy production structures": r"\b((power|energy|wind|solar|hydro|electric) (structures?|generators?|dams?|poles?|lines?|supply|supplies))\b",
    # "homes": r"\b(residential structures|homes?)\b",
    "education structures": r"\b(education(al|learning)? (centers?|centres?|units?|structures?|institutions?)|schools?|universit(y|ies)|colleges?|classrooms?)\b",
    "undefined structures": r"\b((critical|public|undefined|utility) (structures|units?))\b",
    "crop production and forestry": r"\b(crops?|(farm)?lands?|fields?|plantations?|forests?|trees?|bananas?|coffee|cocoa|cotton|maize|rice|sorghum|soybeans?|sugar|tobacco|wheat)\b",
    "agricultural structures": r"\b(irrigation|barns?|farms?(?!\s*land))\b",
    "affected animals": r"\b(livestock|animals?|fish|cows?|sheep|poultr(y|ies)|cattle|goats?|pigs?|chickens?|horses?|heads?)\b",
    "informal settlements": r"\b(camps?|tents?|refuge(e|es)|settlements?|shelters?|huts?|idp (sites?|camps?))\b",
    "EUR": r"\b(euro?s?|€)\b",
    "businesses": r"\b(business(es)?|companies?|industries?|sectors?|enterprises?)\b",
    "null": r"\b(null|none|nan|np.nan)\b",
}

CURRENCY_CONVERTER = {
    # Major currencies
    "EUR": r"\b(euro?s?|€|eur)\b",
    "USD": r"\b(us\s?dollars?|usd|american\s?dollars?|dollars?\s?us)\b|\$\s?us|us\s?\$",
    "GBP": r"\b(pounds? sterling|gbp|£|british pounds?|uk pounds?)\b",
    "JPY": r"\b(japanese yen|jpy|¥|yen)\b",
    "CNY": r"\b(chinese yuan|cny|¥|renminbi|rmb|yuan)\b",
    # Other G20 currencies
    "INR": r"\b(indian rupees?|inr|₹|rupees?)\b",
    "AUD": r"\b(australian dollars?|aud|a\$|dollars? au)\b",
    "CAD": r"\b(canadian dollars?|cad|c\$|dollars? ca)\b",
    "CHF": r"\b(swiss francs?|chf|francs? suisse|fr\.? suisse|frs?\.? suisse)\b",
    "KRW": r"\b(south korean won|krw|₩|won)\b",
    "BRL": r"\b(brazilian reals?|brl|r\$|reais? br)\b",
    "RUB": r"\b(russian rubles?|rub|₽|roubles?)\b",
    "ZAR": r"\b(south african rands?|zar|rands?)\b",
    "TRY": r"\b(turkish lira|try|₺|lira)\b",
    "MXN": r"\b(mexican pesos?|mxn|pesos? mx)\b",
    "IDR": r"\b(indonesian rupiahs?|idr|rupiahs?)\b",
    "SAR": r"\b(saudi riyals?|sar|riyals?)\b",
    "ARS": r"\b(argentine pesos?|ars|pesos? ar)\b",
    # Other major Asian currencies
    "SGD": r"\b(singapore dollars?|sgd|s\$|dollars? sg)\b",
    "HKD": r"\b(hong kong dollars?|hkd|hk\$|dollars? hk)\b",
    "THB": r"\b(thai baht|thb|baht|฿)\b",
    "MYR": r"\b(malaysian ringgits?|myr|ringgits?)\b",
    "PHP": r"\b(philippine pesos?|php|₱|pesos? ph)\b",
    "VND": r"\b(vietnamese dong|vnd|₫|dong)\b",
    "PKR": r"\b(pakistani rupees?|pkr|rupees? pk)\b",
    "BDT": r"\b(bangladeshi taka|bdt|৳|taka)\b",
    "LKR": r"\b(sri lankan rupees?|lkr|rupees? lk)\b",
    "NPR": r"\b(nepalese rupees?|npr|rupees? np)\b",
    "MMK": r"\b(myanmar kyat|mmk|kyat)\b",
    "KHR": r"\b(cambodian riel|khr|៛|riel)\b",
    "LAK": r"\b(laotian kip|lak|₭|kip)\b",
    # Middle East & North Africa
    "AED": r"\b(uae dirhams?|aed|dirhams?)\b",
    "QAR": r"\b(qatari riyals?|qar|riyals? qa)\b",
    "KWD": r"\b(kuwaiti dinars?|kwd|dinars? kw)\b",
    "BHD": r"\b(bahraini dinars?|bhd|dinars? bh)\b",
    "OMR": r"\b(omani riyals?|omr|riyals? om)\b",
    "JOD": r"\b(jordanian dinars?|jod|dinars? jo)\b",
    "ILS": r"\b(israeli shekels?|ils|₪|shekels?|nis)\b",
    "EGP": r"\b(egyptian pounds?|egp|pounds? eg)\b",
    "MAD": r"\b(moroccan dirhams?|mad|dirhams? ma)\b",
    "TND": r"\b(tunisian dinars?|tnd|dinars? tn)\b",
    "DZD": r"\b(algerian dinars?|dzd|dinars? dz)\b",
    "LYD": r"\b(libyan dinars?|lyd|dinars? ly)\b",
    "IQD": r"\b(iraqi dinars?|iqd|dinars? iq)\b",
    "SYP": r"\b(syrian pounds?|syp|pounds? sy)\b",
    "LBP": r"\b(lebanese pounds?|lbp|pounds? lb)\b",
    # Sub-Saharan Africa
    "NGN": r"\b(nigerian naira|ngn|₦|naira)\b",
    "KES": r"\b(kenyan shillings?|kes|shillings? ke)\b",
    "GHS": r"\b(ghanaian cedis?|ghs|₵|cedis?)\b",
    "TZS": r"\b(tanzanian shillings?|tzs|shillings? tz)\b",
    "UGX": r"\b(ugandan shillings?|ugx|shillings? ug)\b",
    "ETB": r"\b(ethiopian birr|etb|birr)\b",
    "XOF": r"\b(cfa franc bceao|xof|francs? cfa)\b",
    "XAF": r"\b(cfa franc beac|xaf|francs? cfa)\b",
    "ZMW": r"\b(zambian kwacha|zmw|kwacha)\b",
    "MWK": r"\b(malawian kwacha|mwk|kwacha mw)\b",
    "BWP": r"\b(botswana pula|bwp|pula)\b",
    "MUR": r"\b(mauritian rupees?|mur|rupees? mu)\b",
    "RWF": r"\b(rwandan francs?|rwf|francs? rw)\b",
    "AOA": r"\b(angolan kwanza|aoa|kwanza)\b",
    "MZN": r"\b(mozambican metical|mzn|metical)\b",
    # Europe
    "NOK": r"\b(norwegian krone|nok|kr|kroner?)\b",
    "SEK": r"\b(swedish krona|sek|kronor?)\b",
    "DKK": r"\b(danish krone|dkk|kroner?)\b",
    "PLN": r"\b(polish zloty|pln|zł|zloty)\b",
    "CZK": r"\b(czech koruna|czk|kč|koruny?)\b",
    "HUF": r"\b(hungarian forint|huf|ft|forint)\b",
    "RON": r"\b(romanian leu|ron|lei)\b",
    "BGN": r"\b(bulgarian lev|bgn|leva)\b",
    "HRK": r"\b(croatian kuna|hrk|kuna)\b",
    "RSD": r"\b(serbian dinars?|rsd|dinars? rs)\b",
    "UAH": r"\b(ukrainian hryvnia|uah|₴|hryvnia)\b",
    "ISK": r"\b(icelandic krona|isk|kronur?)\b",
    "ALL": r"\b(albanian lek|all|lek)\b",
    "MKD": r"\b(macedonian denars?|mkd|denars?)\b",
    "BAM": r"\b(bosnian marks?|bam|marks?)\b",
    "MDL": r"\b(moldovan leu|mdl|lei)\b",
    "GEL": r"\b(georgian lari|gel|₾|lari)\b",
    "AMD": r"\b(armenian dram|amd|֏|dram)\b",
    "AZN": r"\b(azerbaijani manat|azn|₼|manat)\b",
    "BYN": r"\b(belarusian rubles?|byn|rubles? by)\b",
    # Latin America & Caribbean
    "CLP": r"\b(chilean pesos?|clp|pesos? cl)\b",
    "COP": r"\b(colombian pesos?|cop|pesos? co)\b",
    "PEN": r"\b(peruvian soles?|pen|s\/|soles?)\b",
    "VES": r"\b(venezuelan bolivar|ves|bolivares?)\b",
    "UYU": r"\b(uruguayan pesos?|uyu|pesos? uy)\b",
    "PYG": r"\b(paraguayan guarani|pyg|₲|guarani)\b",
    "BOB": r"\b(bolivian boliviano|bob|bolivianos?)\b",
    "CRC": r"\b(costa rican colon|crc|₡|colones?)\b",
    "GTQ": r"\b(guatemalan quetzal|gtq|quetzales?)\b",
    "HNL": r"\b(honduran lempira|hnl|lempiras?)\b",
    "NIO": r"\b(nicaraguan cordoba|nio|cordobas?)\b",
    "PAB": r"\b(panamanian balboa|pab|balboas?)\b",
    "DOP": r"\b(dominican pesos?|dop|pesos? do)\b",
    "HTG": r"\b(haitian gourde|htg|gourdes?)\b",
    "JMD": r"\b(jamaican dollars?|jmd|j\$|dollars? jm)\b",
    "TTD": r"\b(trinidad dollars?|ttd|tt\$|dollars? tt)\b",
    "BBD": r"\b(barbadian dollars?|bbd|bds\$|dollars? bb)\b",
    "BSD": r"\b(bahamian dollars?|bsd|b\$|dollars? bs)\b",
    "XCD": r"\b(east caribbean dollars?|xcd|ec\$)\b",
    # Oceania
    "NZD": r"\b(new zealand dollars?|nzd|nz\$|dollars? nz)\b",
    "FJD": r"\b(fijian dollars?|fjd|fj\$|dollars? fj)\b",
    "PGK": r"\b(papua new guinea kina|pgk|kina)\b",
    "WST": r"\b(samoan tala|wst|tala)\b",
    "TOP": r"\b(tongan pa'anga|top|pa'anga)\b",
    "VUV": r"\b(vanuatu vatu|vuv|vatu)\b",
    "SBD": r"\b(solomon islands dollars?|sbd|si\$|dollars? sb)\b",
    # Central Asia
    "KZT": r"\b(kazakhstani tenge|kzt|₸|tenge)\b",
    "UZS": r"\b(uzbekistani som|uzs|som)\b",
    "TMT": r"\b(turkmen manat|tmt|manats?)\b",
    "TJS": r"\b(tajikistani somoni|tjs|somoni)\b",
    "KGS": r"\b(kyrgyzstani som|kgs|som)\b",
    "AFN": r"\b(afghan afghani|afn|؋|afghani)\b",
    # Special & Historical
    "XAU": r"\b(gold ounces?|xau|oz gold)\b",
    "XAG": r"\b(silver ounces?|xag|oz silver)\b",
    "XPT": r"\b(platinum ounces?|xpt|oz platinum)\b",
    "XDR": r"\b(sdr|special drawing rights?|xdr)\b",
    "BTC": r"\b(bitcoin|btc|₿)\b",
    "ETH": r"\b(ethereum|eth|ether)\b",
}

RESPONSE_UNITS = (
    r"\b(volunteers?|staff|beneficiaries?|branches?|national societies?|trainers?)\b"
)

# dictionary of all possible units for unit identification
ALL_POSSIBLE_UNITS = {}
[
    ALL_POSSIBLE_UNITS.update(d)
    for d in [
        METRIC_UNIT_KW_RECLASS,
        HARMONIZE_UNITS_KW,
        UNIT_KW_RECLASS,
        CURRENCY_CONVERTER,
    ]
]

# list of standard units
STANDARD_UNITS = [
    key
    for unit_dict in [UNIT_TYPE_KW_RECLASS, HARMONIZE_UNITS_KW, UNIT_KW_RECLASS]
    for key in unit_dict.keys()
]
STANDARD_UNITS.append(DEF_CUR)
STANDARD_UNITS.extend(["students", "children"])
STANDARD_UNITS = set(STANDARD_UNITS)
