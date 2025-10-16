class Impacts:
    registry = {}

    @classmethod
    def register(cls, key, main_type, description, keyword=None, expected_unit=None, default_unit=None):
        cls.registry[key] = {
            "main_types": main_type,
            "description": description,
            "keyword": keyword,
            "expected_unit": expected_unit,
            "default_unit": default_unit
        }

    @classmethod
    def get_subtypes(cls):
        return [k for k in cls.registry.keys()]
    @classmethod
    def get_main_types(cls):
        return {k: v["main_types"] for k, v in cls.registry.items()}

    @classmethod
    def get_descriptions(cls):
        return {k: v["description"] for k, v in cls.registry.items()}

    @classmethod
    def get_keywords(cls):
        return {k: v["keyword"] for k, v in cls.registry.items()}

    @classmethod
    def get_expected_units(cls):
        return {k: v["expected_unit"] for k, v in cls.registry.items()}

    @classmethod
    def get_default_units(cls):
        return {k: v["default_unit"] for k, v in cls.registry.items()}

    @classmethod
    def to_dataframe(cls):
        import pandas as pd
        return pd.DataFrame.from_dict(cls.registry, orient="index")
