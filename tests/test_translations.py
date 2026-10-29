"""Translation files stay in sync and cover the mode entities."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

TRANSLATIONS = (
    Path(__file__).parent.parent / "custom_components" / "openwindows" / "translations"
)


def _load(lang: str) -> dict:
    return json.loads((TRANSLATIONS / f"{lang}.json").read_text(encoding="utf-8"))


def _keys(node, prefix=()):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _keys(value, (*prefix, key))
    else:
        yield ".".join(prefix)


def test_en_and_fr_have_identical_key_sets():
    assert set(_keys(_load("en"))) == set(_keys(_load("fr")))


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_entity_translations_cover_new_entities(lang):
    entity = _load(lang)["entity"]
    assert entity["number"]["override_days"]["name"]
    event_states = entity["event"]["airing_reminder"]["state_attributes"]["event_type"][
        "state"
    ]
    assert set(event_states) == {"morning", "office"}
    source_states = entity["sensor"]["mode"]["state_attributes"]["source"]["state"]
    assert set(source_states) == {"auto", "override"}
