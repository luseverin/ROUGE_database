def print_match(matched_df):
    """Display function to better visualize match df"""
    return matched_df[["impactSubtype", "impactSubtype_matched", "impactValue", "impactValue_matched", "impactUnit", "impactUnit_matched", "location", "location_matched", "geometry_sim", "match_sim","valueAnnotation", "annotation_matched"]]