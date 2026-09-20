import json
import logging
import re
from typing import Dict, Any, List, Optional
import httpx

from ..config import settings
from ..schemas.journal import (
    ExtractedJournalIntelligence,
    NutritionSummary,
    NutritionItem,
    ExtractedPerson
)

logger = logging.getLogger("llm_service")

EXTRACTION_SYSTEM_PROMPT = """You are an intelligent extraction engine for a personal Command Centre and Life OS.
Analyze the user's free-form daily journal entry and output a single strictly valid JSON object matching the schema below.

REQUIREMENTS:
1. Nutrition Analysis:
   - Identify all foods and drinks consumed, with portion sizes if mentioned or implied.
   - Provide realistic estimates for calories, protein (g), carbs (g), and fat (g).
   - If user explicitly wrote calorie counts (e.g. 'around 450 cal'), respect and align with that.
   - Calculate total_calories, total_protein_g, total_carbs_g, total_fat_g.
   - Provide confidence score (0.0 to 1.0). If no food/drink was mentioned, return empty items list and 0 totals.

   CRITICAL — Composite / Descriptive Meal Handling:
   - When the user describes the INGREDIENTS or COMPONENTS of a single dish (e.g. "bacon sandwich in a burger bun with butter and brown sauce", "pasta with chicken and parmesan", "wrap with halloumi, lettuce and mayo"), treat the ENTIRE description as ONE food item.
   - Do NOT list "sandwich" and "burger" separately just because both words appear. Words like "bun", "roll", "wrap", "bread" describe the serving vessel of the dish — they are part of the same item.
   - Name the item descriptively: e.g. "Bacon Sandwich (buttered burger bun, brown sauce)" rather than logging "sandwich" + "burger bun" + "bacon" as three separate entries.
   - Only create multiple items when the user clearly describes multiple SEPARATE meals or eating occasions (e.g. "I had cereal for breakfast and a chicken salad for lunch").
   - Estimate macros for the whole assembled dish, not individual components in isolation.

2. Entity & People Extraction:
   - Identify ALL individuals mentioned by name (friends, colleagues, partners, acquaintances, family).
   - CRITICAL: If multiple people are mentioned together (e.g. "met James and Tom", "with Sarah, Dan and Priya"), create a SEPARATE object for EACH person — do not group them into one entry.
   - Context: where they met, what they did, or what was discussed.
   - Sentiment: positive, neutral, or negative.
   - Facts learned: list of new personal facts, preferences, life updates, job roles, hobbies or anything notable shared (e.g. "Likes oat milk flat whites", "Started a new job as Engineering Director", "Training for a marathon"). Leave empty array if nothing specific was shared.
   - Location: specific café, venue, city, or place if mentioned. Null if unknown.
3. Daily Themes & Sentiment:
   - summary: A crisp 1-sentence summary capturing the essence of the day.
   - mood_tag: A 1-2 word mood descriptor (e.g. "Productive", "Reflective", "Energetic", "Social", "Stressed", "Calm", "Exhausted").
   - tags: 3-5 relevant keywords for the day (e.g. ["coffee", "running", "career", "dinner"]).

STRICT JSON SCHEMA:
{
  "nutrition": {
    "items": [
      {
        "name": "string",
        "portion": "string",
        "calories": 0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0
      }
    ],
    "total_calories": 0,
    "total_protein_g": 0.0,
    "total_carbs_g": 0.0,
    "total_fat_g": 0.0,
    "confidence": 0.85
  },
  "people": [
    {
      "name": "string",
      "context": "string",
      "sentiment": "positive | neutral | negative",
      "facts_learned": ["string"],
      "location": "string or null"
    }
  ],
  "summary": "string",
  "mood_tag": "string",
  "tags": ["string"]
}
"""

# Fallback Food Knowledge Base for offline / mock extraction
FOOD_DATABASE = {
    "oatmeal": {"cal": 220, "p": 6, "c": 38, "f": 4, "unit": "1 bowl"},
    "oats": {"cal": 200, "p": 6, "c": 35, "f": 3.5, "unit": "1 serving"},
    "blueberries": {"cal": 45, "p": 0.5, "c": 11, "f": 0.3, "unit": "handful"},
    "berries": {"cal": 50, "p": 0.7, "c": 12, "f": 0.4, "unit": "handful"},
    "banana": {"cal": 105, "p": 1.3, "c": 27, "f": 0.3, "unit": "1 medium"},
    "apple": {"cal": 95, "p": 0.5, "c": 25, "f": 0.3, "unit": "1 medium"},
    "latte": {"cal": 150, "p": 6, "c": 14, "f": 6, "unit": "1 cup"},
    "oat milk latte": {"cal": 140, "p": 3, "c": 18, "f": 5, "unit": "1 cup"},
    "flat white": {"cal": 130, "p": 7, "c": 10, "f": 6, "unit": "1 cup"},
    "coffee": {"cal": 5, "p": 0.3, "c": 0, "f": 0, "unit": "1 mug"},
    "espresso": {"cal": 5, "p": 0.1, "c": 0.5, "f": 0, "unit": "1 shot"},
    "eggs": {"cal": 140, "p": 12, "c": 1, "f": 10, "unit": "2 large eggs"},
    "egg": {"cal": 70, "p": 6, "c": 0.5, "f": 5, "unit": "1 egg"},
    "toast": {"cal": 80, "p": 3, "c": 15, "f": 1, "unit": "1 slice"},
    "sourdough": {"cal": 120, "p": 4, "c": 24, "f": 1, "unit": "1 slice"},
    "avocado toast": {"cal": 280, "p": 6, "c": 26, "f": 16, "unit": "1 slice"},
    "avocado": {"cal": 160, "p": 2, "c": 9, "f": 15, "unit": "1/2 avocado"},
    "protein shake": {"cal": 180, "p": 28, "c": 5, "f": 2.5, "unit": "1 scoop with water"},
    "shake": {"cal": 220, "p": 25, "c": 15, "f": 4, "unit": "1 shake"},
    "chicken": {"cal": 260, "p": 38, "c": 0, "f": 6, "unit": "1 breast (180g)"},
    "chicken breast": {"cal": 260, "p": 38, "c": 0, "f": 6, "unit": "1 breast (180g)"},
    "salmon": {"cal": 320, "p": 34, "c": 0, "f": 18, "unit": "1 fillet (170g)"},
    "steak": {"cal": 450, "p": 46, "c": 0, "f": 28, "unit": "1 steak (220g)"},
    "salad": {"cal": 160, "p": 3, "c": 12, "f": 11, "unit": "1 bowl with dressing"},
    "rice": {"cal": 210, "p": 4.5, "c": 45, "f": 0.5, "unit": "1 cup cooked"},
    "pasta": {"cal": 350, "p": 12, "c": 68, "f": 2, "unit": "1 plate"},
    "pizza": {"cal": 580, "p": 24, "c": 66, "f": 22, "unit": "2 slices"},
    "burger": {"cal": 550, "p": 30, "c": 42, "f": 26, "unit": "1 burger"},
    "sandwich": {"cal": 420, "p": 18, "c": 44, "f": 16, "unit": "1 sandwich"},
    "sushi": {"cal": 420, "p": 16, "c": 65, "f": 7, "unit": "8 rolls"},
    "yogurt": {"cal": 130, "p": 14, "c": 8, "f": 2.5, "unit": "1 pot greek yogurt"},
    "greek yogurt": {"cal": 130, "p": 14, "c": 8, "f": 2.5, "unit": "1 pot"},
    "nuts": {"cal": 180, "p": 5, "c": 6, "f": 16, "unit": "handful (30g)"},
    "almonds": {"cal": 170, "p": 6, "c": 6, "f": 15, "unit": "handful"},
    "protein bar": {"cal": 210, "p": 20, "c": 22, "f": 7, "unit": "1 bar"},
    "burrito": {"cal": 650, "p": 32, "c": 75, "f": 22, "unit": "1 burrito"},
    "tacos": {"cal": 450, "p": 22, "c": 40, "f": 20, "unit": "2 tacos"}
}

class LLMService:
    def __init__(self):
        pass

    async def extract_journal_intelligence(self, raw_text: str, date_str: str) -> ExtractedJournalIntelligence:
        """Processes raw text via Gemini, OpenAI, or intelligent heuristic fallback."""
        if not raw_text or not raw_text.strip():
            return ExtractedJournalIntelligence(
                summary="Empty journal entry.",
                mood_tag="Neutral",
                tags=[]
            )

        # 1. Try Gemini if configured
        if settings.GEMINI_API_KEY and settings.LLM_PROVIDER in ("auto", "gemini"):
            try:
                res = await self._call_gemini(raw_text, date_str)
                if res:
                    return res
            except Exception as e:
                logger.warning(f"Gemini API call failed: {e}. Attempting fallback.")

        # 2. Try OpenAI if configured
        if settings.OPENAI_API_KEY and settings.LLM_PROVIDER in ("auto", "openai"):
            try:
                res = await self._call_openai(raw_text, date_str)
                if res:
                    return res
            except Exception as e:
                logger.warning(f"OpenAI API call failed: {e}. Attempting fallback.")

        # 3. Intelligent Heuristic / Rule-based Fallback
        logger.info("Using built-in intelligent rule-based extraction engine")
        return self._heuristic_extraction(raw_text, date_str)

    async def _call_gemini(self, raw_text: str, date_str: str) -> Optional[ExtractedJournalIntelligence]:
        """Call Gemini, automatically falling back through alternative models on 429/503."""
        primary = settings.GEMINI_MODEL or "gemini-3.5-flash"
        fallbacks = list(settings.GEMINI_FALLBACK_MODELS or [])
        models_to_try = [primary] + [m for m in fallbacks if m != primary]

        # Few-shot example to anchor composite meal + multiple-people handling
        FEW_SHOT_EXAMPLE = """EXAMPLE INPUT:
"Today I woke up and had a bacon sandwich in a burger bun. It was 2 pieces of bacon, buttered bread and some brown sauce. Later I met up with James and Tom at the library to work on the project."

EXAMPLE OUTPUT:
{
  "nutrition": {
    "items": [
      {
        "name": "Bacon Sandwich (burger bun, butter, brown sauce)",
        "portion": "1 sandwich with 2 rashers bacon",
        "calories": 430,
        "protein_g": 22.0,
        "carbs_g": 38.0,
        "fat_g": 18.0
      }
    ],
    "total_calories": 430,
    "total_protein_g": 22.0,
    "total_carbs_g": 38.0,
    "total_fat_g": 18.0,
    "confidence": 0.82
  },
  "people": [
    {
      "name": "James",
      "context": "Met at the library to work on a project",
      "sentiment": "neutral",
      "facts_learned": [],
      "location": "library"
    },
    {
      "name": "Tom",
      "context": "Met at the library to work on a project",
      "sentiment": "neutral",
      "facts_learned": [],
      "location": "library"
    }
  ],
  "summary": "Started the day with a bacon sandwich, then met James and Tom at the library for project work.",
  "mood_tag": "Productive",
  "tags": ["breakfast", "social", "study"]
}

Notice:
- The bacon sandwich is logged as ONE item named descriptively — NOT split into "sandwich" + "burger" + "bacon"
- Both James AND Tom each get their own entry in the people array
- Even when names appear in a list ("James and Tom"), each person gets their own object
---
NOW PROCESS THIS ACTUAL ENTRY:"""

        payload = {
            "system_instruction": {
                "parts": [{"text": EXTRACTION_SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": f"{FEW_SHOT_EXAMPLE}\n\nDate: {date_str}\nJournal Entry:\n\"\"\"\n{raw_text}\n\"\"\""}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            for model_name in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
                logger.info(f"Trying Gemini model: {model_name}")
                resp = await client.post(url, json=payload)

                if resp.status_code in (429, 503):
                    logger.warning(f"Model {model_name} returned {resp.status_code}, trying next fallback...")
                    continue

                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    logger.warning(f"Model {model_name}: no candidates returned")
                    continue

                content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
                logger.info(f"Gemini ({model_name}) raw response: {content_text[:500]}")
                try:
                    parsed_json = json.loads(content_text)
                    result = ExtractedJournalIntelligence(**parsed_json)
                    logger.info(f"Gemini ({model_name}) extraction OK — {len(result.nutrition.items)} food items, {len(result.people)} people")
                    return result
                except Exception as parse_err:
                    logger.error(f"Failed to parse Gemini ({model_name}) response: {parse_err}\nRaw: {content_text}")
                    return None

            logger.error("All Gemini models exhausted (rate limited or errored)")
            return None

    async def _call_openai(self, raw_text: str, date_str: str) -> Optional[ExtractedJournalIntelligence]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Date: {date_str}\nJournal Entry:\n{raw_text}"}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed_json = json.loads(content)
            return ExtractedJournalIntelligence(**parsed_json)

    def _heuristic_extraction(self, raw_text: str, date_str: str) -> ExtractedJournalIntelligence:
        """Deterministic NLP / regex heuristic parser that extracts nutrition, people, and themes."""
        lower_text = raw_text.lower()
        items: List[NutritionItem] = []
        
        # 1. Nutrition matching
        found_foods = set()
        total_cals = 0
        total_p = 0.0
        total_c = 0.0
        total_f = 0.0

        # Sort food items by length descending to match multi-words first (e.g. "oat milk latte" before "latte")
        sorted_foods = sorted(FOOD_DATABASE.keys(), key=len, reverse=True)
        for food_key in sorted_foods:
            if re.search(r'\b' + re.escape(food_key) + r'\b', lower_text):
                # Avoid overlapping substrings already captured
                if any(food_key in existing for existing in found_foods):
                    continue
                found_foods.add(food_key)
                info = FOOD_DATABASE[food_key]
                items.append(NutritionItem(
                    name=food_key.title(),
                    portion=info["unit"],
                    calories=info["cal"],
                    protein_g=info["p"],
                    carbs_g=info["c"],
                    fat_g=info["f"]
                ))
                total_cals += info["cal"]
                total_p += info["p"]
                total_c += info["c"]
                total_f += info["f"]

        # Check if user explicitly wrote calorie count in text like "around 450 cal" or "600 kcal"
        cal_match = re.search(r'(?:around|about|approx|total)?\s*(\d{2,4})\s*(?:cal|cals|calories|kcal)', lower_text)
        if cal_match and not items:
            explicit_cals = int(cal_match.group(1))
            total_cals = explicit_cals
            items.append(NutritionItem(
                name="Logged Meal / Snack",
                portion="1 meal",
                calories=explicit_cals,
                protein_g=round(explicit_cals * 0.05, 1),
                carbs_g=round(explicit_cals * 0.12, 1),
                fat_g=round(explicit_cals * 0.04, 1)
            ))
            total_p = round(explicit_cals * 0.05, 1)
            total_c = round(explicit_cals * 0.12, 1)
            total_f = round(explicit_cals * 0.04, 1)

        nutrition = NutritionSummary(
            items=items,
            total_calories=total_cals,
            total_protein_g=round(total_p, 1),
            total_carbs_g=round(total_c, 1),
            total_fat_g=round(total_f, 1),
            confidence=0.85 if items else 0.5
        )

        # 2. People & Entity Extraction
        people: List[ExtractedPerson] = []
        # Pattern 1: "Met [Name]", "Caught up with [Name]", "Coffee with [Name]", "Talked to [Name]", "Dinner with [Name]"
        meeting_matches = re.finditer(
            r'\b(?:met|met with|caught up with|coffee with|lunch with|dinner with|drinks with|talked with|talked to|called|chat with|meeting with|synced with)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            raw_text,
            re.IGNORECASE
        )
        
        seen_names = []
        for m in meeting_matches:
            name = m.group(1).strip()
            # Filter common false positives
            if name.lower() in ("today", "yesterday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "morning", "afternoon", "evening", "lunch", "dinner"):
                continue
            if name not in seen_names:
                seen_names.append(name)

        # Pattern 2: Sentences starting with or mentioning a person doing something
        person_facts_matches = re.finditer(
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:told me|shared that|mentioned|started|likes|prefers|is working on|joined|promoted to|is currently|was promoted to)\s+([^.!?]+)',
            raw_text,
            re.IGNORECASE
        )
        facts_by_person: Dict[str, List[str]] = {}
        for m in person_facts_matches:
            subj = m.group(1).strip()
            fact_clause = m.group(2).strip()
            verb_matched = re.search(r'\b(told me|shared that|mentioned|started|likes|prefers|is working on|joined|promoted to|is currently|was promoted to)\b', m.group(0), re.IGNORECASE)
            verb = verb_matched.group(0) if verb_matched else ""
            fact = f"{verb} {fact_clause}".strip()

            target_person = None
            if subj.lower() in ("he", "she") and seen_names:
                # Attribute to the most recently mentioned person
                target_person = seen_names[-1]
            elif subj.lower() not in ("i", "we", "he", "she", "they", "it", "my", "today"):
                target_person = subj
                if target_person not in seen_names:
                    seen_names.append(target_person)

            if target_person:
                facts_by_person.setdefault(target_person, []).append(fact)

        # Extract context snippets and locations for each detected person
        for name in seen_names:
            # Find sentence mentioning this name
            sentence = ""
            for s in re.split(r'[.!?]+', raw_text):
                if re.search(r'\b' + re.escape(name) + r'\b', s):
                    sentence = s.strip()
                    break
            
            # Location extraction heuristic (e.g. "at [Place]", "in [Place]")
            location = None
            loc_match = re.search(r'(?:at|in)\s+([A-Z][A-Za-z0-9\s&\'\.-]+?)(?:,|\.|\s+with|\s+to|\s+for|$)', sentence)
            if loc_match:
                candidate_loc = loc_match.group(1).strip()
                if len(candidate_loc) > 2 and candidate_loc.lower() not in ("the", "this", "that"):
                    location = candidate_loc

            # Sentiment heuristic
            sentiment = "positive" if any(w in sentence.lower() for w in ["great", "promoted", "excited", "happy", "fun", "lovely", "productive", "awesome"]) else (
                "negative" if any(w in sentence.lower() for w in ["stressed", "annoyed", "unfortunate", "bad", "sad", "tired"]) else "neutral"
            )

            people.append(ExtractedPerson(
                name=name,
                context=sentence or f"Interaction with {name}",
                sentiment=sentiment,
                facts_learned=facts_by_person.get(name, []),
                location=location
            ))

        # 3. Mood & Themes
        mood_tag = "Reflective"
        if any(w in lower_text for w in ["run", "workout", "energetic", "productive", "crushed", "great day", "fast"]):
            mood_tag = "Productive & Energetic"
        elif any(w in lower_text for w in ["tired", "exhausted", "sleepy", "drained"]):
            mood_tag = "Exhausted"
        elif any(w in lower_text for w in ["social", "friends", "met", "dinner", "drinks", "coffee"]):
            mood_tag = "Social & Connected"
        elif any(w in lower_text for w in ["stress", "anxious", "hectic", "busy"]):
            mood_tag = "Hectic"
        elif any(w in lower_text for w in ["calm", "peaceful", "relaxing", "reading"]):
            mood_tag = "Calm & Grounded"

        # 1-sentence summary
        sentences = [s.strip() for s in re.split(r'[.!?]+', raw_text) if len(s.strip()) > 5]
        summary = sentences[0] if sentences else raw_text[:120]
        if not summary.endswith("."):
            summary += "."

        # Tags
        tags = []
        if items:
            tags.append("nutrition")
        if people:
            tags.append("social")
        if any(w in lower_text for w in ["run", "gym", "workout", "cycling", "walk"]):
            tags.append("fitness")
        if any(w in lower_text for w in ["work", "meeting", "code", "project", "client", "office"]):
            tags.append("work")
        if any(w in lower_text for w in ["coffee", "café", "espresso"]):
            tags.append("coffee")
        if not tags:
            tags = ["daily", "journal"]

        return ExtractedJournalIntelligence(
            nutrition=nutrition,
            people=people,
            summary=summary,
            mood_tag=mood_tag,
            tags=tags
        )

llm_service = LLMService()
