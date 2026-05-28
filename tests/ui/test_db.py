from ui.db import (
    count_areas,
    get_area_hierarchy,
    get_area_meta,
    get_area_stats,
    get_areas_meta,
    get_comparison_data,
    get_municipalities,
    load_translations,
    search_areas,
    translate,
)


# --- translations ---

def test_load_translations_returns_dict():
    t = load_translations()
    assert isinstance(t, dict)
    assert len(t) > 400


def test_known_translation():
    assert translate("Inwoners", "en") == "Residents"


def test_dutch_passthrough():
    assert translate("Inwoners", "nl") == "Inwoners"


def test_missing_term_fallback():
    assert translate("__onbekend__", "en") == "__onbekend__"


def test_category_translation():
    assert translate("Bevolking", "en") == "Demographics"


def test_area_type_translation():
    assert translate("buurt", "en") == "neighbourhood"


# --- get_municipalities ---

def test_get_municipalities_returns_sorted_list():
    municipalities = get_municipalities()
    assert municipalities == sorted(municipalities)
    assert "amsterdam" in municipalities
    assert "haarlem" in municipalities


# --- count_areas / search_areas ---

def test_count_areas_returns_total():
    assert count_areas("") == 3


def test_count_areas_with_query():
    assert count_areas("pijp") == 1


def test_count_areas_filter_by_municipality():
    assert count_areas("", municipality="haarlem") == 1


def test_search_returns_matching_areas():
    results = search_areas("pijp")
    assert len(results) == 1
    assert results[0]["area_slug"] == "de-pijp-amsterdam"


def test_search_empty_query_returns_all():
    results = search_areas("")
    assert len(results) == 3


def test_search_filter_by_municipality():
    results = search_areas("", municipality="haarlem")
    assert all(r["municipality"] == "haarlem" for r in results)
    assert len(results) == 1


def test_search_filter_by_type():
    results = search_areas("", area_type="wijk")
    assert all(r["area_type"] == "wijk" for r in results)
    assert len(results) == 1


def test_search_result_keys():
    results = search_areas("oud")
    assert set(results[0].keys()) >= {"area_slug", "area_name", "area_type", "municipality"}


def test_search_pagination_page2_empty():
    results = search_areas("", page=2)
    assert results == []


# --- get_area_meta ---

def test_get_area_meta_returns_dict():
    meta = get_area_meta("oud-west-amsterdam")
    assert meta is not None
    assert meta["area_name"] == "Oud-West"
    assert meta["area_type"] == "wijk"
    assert meta["municipality"] == "amsterdam"


def test_get_area_meta_missing_slug_returns_none():
    assert get_area_meta("does-not-exist") is None


# --- get_area_stats ---

def test_get_area_stats_returns_grouped():
    stats = get_area_stats("oud-west-amsterdam")
    assert "Bevolking" in stats
    assert stats["Bevolking"][0]["topic"] == "Inwoners"
    assert stats["Bevolking"][0]["value"] == "25000"


def test_get_area_stats_with_query_filters():
    stats = get_area_stats("oud-west-amsterdam", q="inkomen")
    assert "Bevolking" not in stats
    assert "Inkomen" in stats


def test_get_area_stats_empty_query_returns_all():
    stats = get_area_stats("oud-west-amsterdam")
    total = sum(len(rows) for rows in stats.values())
    assert total == 5


# --- get_area_hierarchy ---

def test_hierarchy_for_buurt_returns_parent_wijk():
    h = get_area_hierarchy("de-pijp-amsterdam", "buurt")
    assert h["parent_wijk"]["wijk_slug"] == "oud-west-amsterdam"
    assert h["parent_wijk"]["wijk_name"] == "Oud-West"


def test_hierarchy_for_buurt_with_no_siblings():
    h = get_area_hierarchy("de-pijp-amsterdam", "buurt")
    assert h["siblings"] == []


def test_hierarchy_for_wijk_returns_buurten():
    h = get_area_hierarchy("oud-west-amsterdam", "wijk")
    assert len(h["buurten"]) == 1
    assert h["buurten"][0]["buurt_slug"] == "de-pijp-amsterdam"


def test_hierarchy_for_unknown_buurt_returns_empty():
    h = get_area_hierarchy("does-not-exist", "buurt")
    assert h == {}


# --- get_areas_meta ---

def test_get_areas_meta_returns_dict():
    result = get_areas_meta(["oud-west-amsterdam"])
    assert "oud-west-amsterdam" in result
    assert result["oud-west-amsterdam"]["area_name"] == "Oud-West"


def test_get_areas_meta_multiple_slugs():
    result = get_areas_meta(["oud-west-amsterdam", "de-pijp-amsterdam"])
    assert set(result.keys()) == {"oud-west-amsterdam", "de-pijp-amsterdam"}


def test_get_areas_meta_empty_slugs_returns_empty():
    assert get_areas_meta([]) == {}


# --- get_comparison_data ---

def test_get_comparison_data_returns_nested():
    result = get_comparison_data(["oud-west-amsterdam", "de-pijp-amsterdam"], {"Inwoners"})
    assert "Inwoners" in result
    assert "oud-west-amsterdam" in result["Inwoners"]
    assert result["Inwoners"]["oud-west-amsterdam"]["value"] == "25000"


def test_get_comparison_data_missing_area_omitted():
    result = get_comparison_data(["oud-west-amsterdam", "de-pijp-amsterdam"], {"Inwoners"})
    assert "de-pijp-amsterdam" in result["Inwoners"]


def test_get_comparison_data_no_topics_returns_empty():
    assert get_comparison_data(["oud-west-amsterdam"], set()) == {}


def test_get_comparison_data_no_slugs_returns_empty():
    assert get_comparison_data([], {"Inwoners"}) == {}
