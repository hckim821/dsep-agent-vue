"""Unit tests for the deterministic helpers in wiki_pipeline.

These tests do not require a running vLLM or DB — they cover the pure-Python
helpers (parsing, regex, path-traversal guards, attribution).
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


# -- wiki_repo --------------------------------------------------------------


def test_extract_backlinks_finds_double_bracket_links():
    from wiki_pipeline.wiki_repo import extract_backlinks

    content = "See [[Transformer]] and also [[BERT]] for details."
    links = extract_backlinks(content)
    assert "Transformer" in links
    assert "BERT" in links


def test_extract_backlinks_handles_empty_or_none():
    from wiki_pipeline.wiki_repo import extract_backlinks

    assert extract_backlinks("") == []
    assert extract_backlinks(None) == []


def test_extract_backlinks_strips_whitespace():
    from wiki_pipeline.wiki_repo import extract_backlinks

    links = extract_backlinks("Look at [[  Spaced Title  ]] here.")
    assert "Spaced Title" in links


# -- ingest helpers ---------------------------------------------------------


def test_parse_page_plan_pure_json():
    from wiki_pipeline.ingest import _parse_page_plan

    plan = _parse_page_plan(
        '{"create": ["concepts/foo.md"], "update": ["entities/bar.md"], "cross_ref": []}'
    )
    assert plan["create"] == ["concepts/foo.md"]
    assert plan["update"] == ["entities/bar.md"]
    assert plan["cross_ref"] == []


def test_parse_page_plan_embedded_in_prose():
    from wiki_pipeline.ingest import _parse_page_plan

    response = (
        "Based on the new content I will create one new page.\n"
        '{"create": ["concepts/llm.md"], "update": [], "cross_ref": []}\n'
        "Done."
    )
    plan = _parse_page_plan(response)
    assert "concepts/llm.md" in plan["create"]


def test_parse_page_plan_with_code_fence():
    from wiki_pipeline.ingest import _parse_page_plan

    response = (
        "Here is the plan:\n"
        "```json\n"
        '{"create": ["a.md"], "update": ["b.md"], "cross_ref": ["c.md"]}\n'
        "```\n"
    )
    plan = _parse_page_plan(response)
    assert plan["create"] == ["a.md"]
    assert plan["update"] == ["b.md"]
    assert plan["cross_ref"] == ["c.md"]


def test_parse_page_plan_handles_garbage():
    from wiki_pipeline.ingest import _parse_page_plan

    plan = _parse_page_plan("the model said something unhelpful")
    assert plan == {"create": [], "update": [], "cross_ref": []}


def test_add_source_attribution_adds_section():
    from wiki_pipeline.ingest import _add_source_attribution

    content = "# Test Page\n\nSome content."
    result = _add_source_attribution(content, 42, "Test Post")
    assert "## 출처" in result
    assert "Ingest #42" in result
    assert "Test Post" in result


def test_add_source_attribution_extends_existing_section():
    from wiki_pipeline.ingest import _add_source_attribution

    content = "# Page\n\nBody.\n\n## 출처\n- Ingest #1: First post\n"
    result = _add_source_attribution(content, 7, "Second post")
    # Existing section should be retained, new entry appended
    assert "Ingest #1: First post" in result
    assert "Ingest #7: Second post" in result
    # And we should not have created a duplicate `## 출처` heading
    assert result.count("## 출처") == 1


def test_add_source_attribution_idempotent_for_same_post():
    from wiki_pipeline.ingest import _add_source_attribution

    base = "# Page\n\nBody.\n\n## 출처\n- Ingest #5: Same post\n"
    once = _add_source_attribution(base, 5, "Same post")
    assert once.count("Ingest #5: Same post") == 1


def test_extract_title_returns_first_h1():
    from wiki_pipeline.ingest import _extract_title

    assert _extract_title("# Foo\n\n## Bar\n") == "Foo"
    assert _extract_title("no heading here") is None


# -- storage path-traversal guards -----------------------------------------


def test_safe_post_dir_creates_under_base(monkeypatch):
    from wiki_pipeline import storage

    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("STORAGE_BASE_PATH", tmp)
        path = storage.safe_post_dir(123, "original")
        assert path.exists()
        assert str(path).startswith(str(Path(tmp).resolve()))


def test_save_upload_rejects_bad_extension(monkeypatch):
    from wiki_pipeline import storage

    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("STORAGE_BASE_PATH", tmp)
        with pytest.raises(ValueError, match="Extension not allowed"):
            storage.save_upload(1, "exploit.exe", b"data")


def test_save_upload_rejects_oversize(monkeypatch):
    from wiki_pipeline import storage

    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("STORAGE_BASE_PATH", tmp)
        big = b"x" * (storage.MAX_FILE_SIZE + 1)
        with pytest.raises(ValueError, match="File too large"):
            storage.save_upload(1, "x.png", big)


def test_save_upload_round_trip(monkeypatch):
    from wiki_pipeline import storage

    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("STORAGE_BASE_PATH", tmp)
        info = storage.save_upload(42, "diagram.png", b"\x89PNGfake")
        assert info["size_bytes"] == len(b"\x89PNGfake")
        assert info["stored_filename"].endswith(".png")
        # Returned path is relative to storage base
        full = Path(tmp) / info["file_path"]
        assert full.read_bytes() == b"\x89PNGfake"


def test_get_file_path_blocks_traversal(monkeypatch):
    from wiki_pipeline import storage

    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("STORAGE_BASE_PATH", tmp)
        with pytest.raises(ValueError):
            storage.get_file_path("../../etc/passwd")
