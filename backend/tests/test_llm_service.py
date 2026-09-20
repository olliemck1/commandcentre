import pytest
from app.services.llm_service import llm_service

def test_heuristic_nutrition_extraction():
    text = "Had a bowl of oatmeal with blueberries and an oat milk latte (around 450 cal)."
    intel = llm_service._heuristic_extraction(text, "2026-09-20")

    assert intel.nutrition is not None
    assert intel.nutrition.total_calories > 0
    # Oatmeal, blueberries, oat milk latte should be parsed
    food_names = [item.name.lower() for item in intel.nutrition.items]
    assert any("oatmeal" in name or "oats" in name for name in food_names)
    assert any("latte" in name for name in food_names)
    assert intel.nutrition.total_protein_g > 0

def test_heuristic_people_and_facts_extraction():
    text = "Met Sarah Miller at Monmouth Coffee. She told me she was promoted to Engineering Director and likes flat whites."
    intel = llm_service._heuristic_extraction(text, "2026-09-20")

    assert len(intel.people) > 0
    names = [p.name for p in intel.people]
    assert any("Sarah" in name for name in names)
    
    sarah = next(p for p in intel.people if "Sarah" in p.name)
    assert len(sarah.facts_learned) > 0
    assert any("Director" in f or "promoted" in f or "flat white" in f or "likes" in f for f in sarah.facts_learned)

def test_empty_journal_entry():
    intel = llm_service._heuristic_extraction("", "2026-09-20")
    assert intel.nutrition.total_calories == 0
    assert len(intel.people) == 0
