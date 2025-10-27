from src.LLM_functions import deduplicate_structured_responses
prev_resp = [ext_appeal.loc[id].to_dict() for id in [298,302]]
new_resp = [ext_appeal.loc[id].to_dict() for id in [304,305]]
len(deduplicate_structured_responses(prev_resp, new_resp))
deduplicate_structured_responses([{"impactSubtype": "Affected People", "impactValue": 100, "impactUnit": "percent"},
                                 {"impactSubtype": "Affected People", "impactValue": np.nan, "impactUnit": np.nan},
                                 {"impactSubtype": "Affected People", "impactValue": 100, "impactUnit": np.nan}],
                                 [{"impactSubtype": "Affected People", "impactValue": 100, "impactUnit": "percent"},
                                 {"impactSubtype": "Affected People", "impactValue": np.nan, "impactUnit": np.nan},
                                 {"impactSubtype": "Affected People", "impactValue": np.nan, "impactUnit": "people"},
                                 {"impactSubtype": "Affected People", "impactValue": 100, "impactUnit": np.nan}])
from price_parser import Price
test_price_true1 = "1,500 USD"
parsed_price1 = Price.fromstring(test_price_true1)
print(parsed_price1)

test_price_true2 = "735 billion CHF"
parsed_price2 = Price.fromstring(test_price_true2)
print(parsed_price2)

test_price_wrong = "1,500"
parsed_price2 = Price.fromstring(test_price_wrong)
print(parsed_price2)

test_price_wrong = "1,500 PHP"
parsed_price2 = Price.fromstring(test_price_wrong)
print(parsed_price2)
from currency_converter import CurrencyConverter
c = CurrencyConverter()
test_conv_pass =(1500, "USD")
DEF_CUR = "EUR"
conv_price_pass = c.convert(test_conv_pass[0], test_conv_pass[1], DEF_CUR)
print(conv_price_pass)
test_conv_fail = (1500, "foo")
try:
    conv_price_fail = c.convert(test_conv_fail[0], test_conv_fail[1], DEF_CUR)
    print(conv_price_fail)
except Exception as e:
    print(e)
test_conv_fail2 = ("asda", "USD")
try:
    conv_price_fail2 = c.convert(test_conv_fail2[0], test_conv_fail2[1], DEF_CUR)
    print(conv_price_fail2)
except Exception as e:
    print(e)
parsed_price1.currency
unit_type = "kg"
unit = "kg of crops"
[unit_corr for unit_corr in unit_kw_reclass.keys() if re.search(unit_kw_reclass[unit_corr], unit, re.IGNORECASE)]

test_df = pd.DataFrame({
        "reportDate": ["2020-01-01", "2020-01-01", "2020-01-01"],
        "impactSubtype": ["Affected People", "Crop Production and Forestry", "Crop Production and Forestry"],
        "impactValue": [1000,1000,100],
        "impactUnit": ["families", "kg of crops","hectares of crops"]})
#replace numbers in units
test_df[["impactValue", "impactUnit"]] = test_df.apply(replace_numbers_unit, axis=1)
#convert money
test_df[["impactValue", "impactUnit"]] = test_df.apply(convert_monetary_units, axis=1)
#standardize SI units
test_df[["impactValue", "impactUnit"]]  = test_df.apply(standardize_metric_units, std_unit_kw_reclass=std_unit_kw_reclass, unit_mapping=unit_mapping, axis=1)
test_df = test_df.apply(convert_unit, unit_converter=unit_converter, axis=1)
test_df["unit_type"] = test_df.apply(assign_unit_type, unit_type_kw_reclass=unit_type_kw_reclass, axis=1)
test_df["impactUnit"] = test_df.apply(reclassify_units, unit_kw_reclass=unit_kw_reclass, default_subtype_unit=default_subtype_unit, force_unit_to_subtype=force_unit_to_subtype, axis=1)
test_df