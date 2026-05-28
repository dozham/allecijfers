from unittest.mock import AsyncMock

import pytest


def test_index_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "AlleCijfers" in resp.text


def test_index_has_municipality_options(client):
    resp = client.get("/")
    assert 'value="amsterdam"' in resp.text
    assert 'value="haarlem"' in resp.text


def test_index_has_search_input(client):
    resp = client.get("/")
    assert 'type="search"' in resp.text
    assert 'hx-get="/search"' in resp.text


def test_search_returns_results(client):
    resp = client.get("/search?q=pijp")
    assert resp.status_code == 200
    assert "De Pijp" in resp.text


def test_search_empty_returns_all(client):
    resp = client.get("/search?q=")
    assert resp.status_code == 200
    assert "Oud-West" in resp.text
    assert "De Pijp" in resp.text


def test_search_filter_by_municipality(client):
    resp = client.get("/search?q=&municipality=haarlem")
    assert resp.status_code == 200
    assert "Centrum" in resp.text
    assert "Oud-West" not in resp.text


def test_search_filter_by_type(client):
    resp = client.get("/search?q=&type=wijk")
    assert resp.status_code == 200
    assert "Oud-West" in resp.text
    assert "De Pijp" not in resp.text


def test_area_returns_200(client):
    resp = client.get("/area/oud-west-amsterdam")
    assert resp.status_code == 200
    assert "Oud-West" in resp.text


def test_area_shows_summary_cards(client):
    resp = client.get("/area/oud-west-amsterdam")
    assert "25000" in resp.text
    assert "35000" in resp.text


def test_area_shows_stats_tables(client):
    resp = client.get("/area/oud-west-amsterdam")
    assert "Bevolking" in resp.text
    assert "Inwoners" in resp.text


def test_area_not_found_returns_404(client):
    resp = client.get("/area/does-not-exist")
    assert resp.status_code == 404


def test_area_stats_partial(client):
    resp = client.get("/area/oud-west-amsterdam/stats?q=inkomen")
    assert resp.status_code == 200
    assert "Inkomen" in resp.text
    assert "Bevolking" not in resp.text


def test_area_stats_partial_empty_query(client):
    resp = client.get("/area/oud-west-amsterdam/stats?q=")
    assert resp.status_code == 200
    assert "Bevolking" in resp.text
    assert "Inkomen" in resp.text


def test_area_shows_hierarchy_buurten(client):
    resp = client.get("/area/oud-west-amsterdam")
    assert "De Pijp" in resp.text
    assert "/area/de-pijp-amsterdam" in resp.text


def test_area_shows_parent_wijk_link(client):
    resp = client.get("/area/de-pijp-amsterdam")
    assert "/area/oud-west-amsterdam" in resp.text


def test_set_lang_nl_to_en(client):
    resp = client.post("/set-lang", data={"lang": "en"}, headers={"referer": "/"})
    assert resp.status_code == 200
    assert client.cookies.get("lang") == "en"


def test_set_lang_invalid_defaults_to_nl(client):
    resp = client.post("/set-lang", data={"lang": "fr"}, headers={"referer": "/"})
    assert resp.status_code == 200
    assert client.cookies.get("lang") == "nl"


def test_index_default_theme_is_dark(client):
    resp = client.get("/")
    assert 'data-theme="dark"' in resp.text


def test_set_theme_to_light(client):
    resp = client.post("/set-theme", data={"theme": "light"}, headers={"referer": "/"})
    assert resp.status_code == 200
    assert client.cookies.get("theme") == "light"


def test_set_theme_invalid_defaults_to_dark(client):
    resp = client.post("/set-theme", data={"theme": "solarized"}, headers={"referer": "/"})
    assert resp.status_code == 200
    assert client.cookies.get("theme") == "dark"


def test_star_topic_sets_cookie(client):
    resp = client.post("/area/oud-west-amsterdam/star", data={"topic": "Inwoners", "q": ""})
    assert resp.status_code == 200
    assert "Inwoners" in client.cookies.get("starred", "")


def test_star_topic_shows_pinned_group(client):
    client.cookies.set("starred", "Inwoners")
    resp = client.get("/area/oud-west-amsterdam")
    assert "Favorieten" in resp.text or "Starred" in resp.text


def test_unstar_topic_removes_from_cookie(client):
    client.post("/area/oud-west-amsterdam/star", data={"topic": "Inwoners", "q": ""})
    client.post("/area/oud-west-amsterdam/star", data={"topic": "Inwoners", "q": ""})
    all_starred = [c.value for c in client.cookies.jar if c.name == "starred"]
    assert not any("Inwoners" in v for v in all_starred)


def test_area_english_lang(client):
    client.cookies.set("lang", "en")
    resp = client.get("/area/oud-west-amsterdam")
    assert resp.status_code == 200
    assert "Residents" in resp.text or "Demographics" in resp.text


def test_compare_add_sets_cookie(client):
    resp = client.post("/compare/add", data={"slug": "oud-west-amsterdam"})
    assert resp.status_code == 200
    assert "oud-west-amsterdam" in client.cookies.get("compare", "")


def test_compare_add_second_slug_appends(client):
    client.post("/compare/add", data={"slug": "oud-west-amsterdam"})
    client.post("/compare/add", data={"slug": "de-pijp-amsterdam"})
    compare = client.cookies.get("compare", "")
    assert "oud-west-amsterdam" in compare
    assert "de-pijp-amsterdam" in compare


def test_compare_remove_removes_slug(client):
    client.post("/compare/add", data={"slug": "oud-west-amsterdam"})
    client.post("/compare/add", data={"slug": "de-pijp-amsterdam"})
    client.post("/compare/remove", data={"slug": "oud-west-amsterdam"})
    compare = client.cookies.get("compare", "")
    assert "oud-west-amsterdam" not in compare
    assert "de-pijp-amsterdam" in compare


def test_compare_clear_empties_cookie(client):
    client.post("/compare/add", data={"slug": "oud-west-amsterdam"})
    client.post("/compare/clear", data={})
    assert "oud-west-amsterdam" not in client.cookies.get("compare", "")


def test_compare_page_empty_state(client):
    resp = client.get("/compare")
    assert resp.status_code == 200
    assert "Geen gebieden" in resp.text or "No areas" in resp.text


def test_compare_page_with_slugs_and_starred(client):
    client.cookies.set("compare", "oud-west-amsterdam|de-pijp-amsterdam")
    client.cookies.set("starred", "Inwoners")
    resp = client.get("/compare")
    assert resp.status_code == 200
    assert "Oud-West" in resp.text
    assert "De Pijp" in resp.text
    assert "25000" in resp.text
    assert "15000" in resp.text


def test_compare_page_no_starred_shows_prompt(client):
    client.cookies.set("compare", "oud-west-amsterdam|de-pijp-amsterdam")
    resp = client.get("/compare")
    assert resp.status_code == 200
    assert "Geen favoriete" in resp.text or "No starred" in resp.text


def test_area_page_shows_add_to_compare_button(client):
    resp = client.get("/area/oud-west-amsterdam")
    assert "+ Vergelijk" in resp.text or "Add to compare" in resp.text


def test_area_page_shows_in_comparison_when_added(client):
    client.cookies.set("compare", "oud-west-amsterdam")
    resp = client.get("/area/oud-west-amsterdam")
    assert "In vergelijking" in resp.text or "In comparison" in resp.text


def test_crawl_start_valid_municipality(client, monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr("ui.main._launch_crawl", mock)
    resp = client.post("/crawl/start", data={"municipality": "rotterdam"})
    assert resp.status_code == 200
    assert "rotterdam" in resp.text
    assert "alert-success" in resp.text
    mock.assert_called_once_with("rotterdam")


def test_crawl_start_normalizes_input(client, monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr("ui.main._launch_crawl", mock)
    resp = client.post("/crawl/start", data={"municipality": "  Rotterdam  "})
    assert resp.status_code == 200
    assert "rotterdam" in resp.text
    assert "alert-success" in resp.text
    mock.assert_called_once_with("rotterdam")


def test_crawl_start_empty_municipality_returns_error(client):
    resp = client.post("/crawl/start", data={"municipality": ""})
    assert resp.status_code == 200
    assert "alert-error" in resp.text


def test_crawl_start_invalid_chars_returns_error(client):
    resp = client.post("/crawl/start", data={"municipality": "den haag!"})
    assert resp.status_code == 200
    assert "alert-error" in resp.text


def test_index_has_crawl_modal_trigger(client):
    resp = client.get("/")
    assert "crawl-modal" in resp.text
    assert 'hx-post="/crawl/start"' in resp.text
