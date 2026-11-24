"""Unified LLM service interface and adapters.

Provides:
- LLMInterface: Protocol defining chat_with_tools, structured_output, and transcribe.
- GeminiAdapter: google-genai SDK implementation with HttpOptions(api_version="v1beta").
- OpenAICompatibleAdapter: standard OpenAI implementation covering GitHub Models, Azure, Ollama, etc.
- MockLLMAdapter: deterministic local evaluation fallback.
"""
import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel

from ..config import settings

logger = logging.getLogger("llm_service")

class LLMInterface(ABC):
    @abstractmethod
    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system_prompt: str,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """Runs a chat turn. Returns dict with:
        - content: Optional[str] (model textual reply, or None if tool call)
        - tool_calls: List[Dict[str, Any]] (list of {id, name, args})
        """
        pass

    @abstractmethod
    async def structured_output(
        self,
        schema: Type[BaseModel],
        prompt: str,
        system_prompt: str,
        temperature: float = 0.1
    ) -> BaseModel:
        """Parses output strictly matching the provided Pydantic model."""
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/ogg",
        prompt: Optional[str] = None
    ) -> Optional[str]:
        """Transcribes speech into clear verbatim English text."""
        pass


class GeminiAdapter(LLMInterface):
    def __init__(self, api_key: str, model_name: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required for Gemini adapter")
        if not model_name:
            raise ValueError("Configured Gemini model name cannot be empty")
        self.api_key = api_key
        self.model_name = model_name

        try:
            from google import genai
            from google.genai import types
            # Pinned to v1beta for model aliases resolution
            self.client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(api_version="v1beta")
            )
        except Exception as e:
            logger.error(f"Failed to initialize google-genai client: {e}")
            raise

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system_prompt: str,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        from google.genai import types
        from google.genai.errors import APIError

        # Convert tool definitions to Gemini function declarations
        function_declarations = []
        for t in tools:
            decl = {
                "name": t["name"],
                "description": t["description"],
                "parameters": t.get("parameters", {"type": "object", "properties": {}})
            }
            function_declarations.append(decl)

        gemini_tools = [{"function_declarations": function_declarations}] if function_declarations else None

        # Build contents
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else ("model" if msg["role"] == "assistant" else "user")
            parts = []
            if msg.get("content"):
                parts.append({"text": str(msg["content"])})
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    parts.append({
                        "function_call": {
                            "name": tc["name"],
                            "args": tc["args"]
                        }
                    })
            if msg.get("role") == "tool":
                parts.append({
                    "function_response": {
                        "name": msg.get("name", "tool"),
                        "response": {"result": msg.get("content")}
                    }
                })
            if parts:
                contents.append({"role": role, "parts": parts})

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            tools=gemini_tools
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )

            tool_calls = []
            text_content = ""

            if response.candidates and response.candidates[0].content:
                for part in response.candidates[0].content.parts:
                    if getattr(part, "function_call", None):
                        fc = part.function_call
                        tool_calls.append({
                            "id": getattr(fc, "id", None) or f"call_{fc.name}",
                            "name": fc.name,
                            "args": dict(fc.args) if fc.args else {}
                        })
                    elif getattr(part, "text", None):
                        text_content += part.text

            return {
                "content": text_content if text_content else None,
                "tool_calls": tool_calls
            }
        except APIError as api_err:
            logger.error(f"Gemini APIError: {api_err}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Gemini chat: {e}")
            raise

    async def structured_output(
        self,
        schema: Type[BaseModel],
        prompt: str,
        system_prompt: str,
        temperature: float = 0.1
    ) -> BaseModel:
        from google.genai import types
        from google.genai.errors import APIError

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=schema
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            raw_text = response.text or "{}"
            parsed = json.loads(raw_text)
            return schema(**parsed)
        except APIError as api_err:
            logger.error(f"Gemini APIError in structured_output: {api_err}")
            raise
        except Exception as e:
            logger.error(f"Gemini structured_output failed: {e}")
            raise

    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/ogg",
        prompt: Optional[str] = None
    ) -> Optional[str]:
        from google.genai import types
        from google.genai.errors import APIError

        transcribe_prompt = prompt or "Please transcribe the speech in this audio file verbatim into clear English text. Output ONLY the raw transcription."
        try:
            part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[part, transcribe_prompt]
            )
            return response.text.strip() if response.text else None
        except APIError as api_err:
            logger.error(f"Gemini APIError in transcribe: {api_err}")
            return None
        except Exception as e:
            logger.error(f"Gemini audio transcription error: {e}")
            return None


class OpenAICompatibleAdapter(LLMInterface):
    def __init__(self, api_key: str, model_name: str, base_url: Optional[str] = None):
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI adapter")
        if not model_name:
            raise ValueError("Configured OpenAI model name cannot be empty")
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url or None

        import openai
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system_prompt: str,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        openai_tools = []
        for t in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t.get("parameters", {"type": "object", "properties": {}})
                }
            })

        formatted_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            formatted_messages.append(m)

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "messages": formatted_messages,
            "temperature": temperature
        }
        if openai_tools:
            kwargs["tools"] = openai_tools

        try:
            response = self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            msg = choice.message

            tool_calls = []
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    args = {}
                    if tc.function.arguments:
                        try:
                            args = json.loads(tc.function.arguments)
                        except Exception:
                            args = {}
                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "args": args
                    })

            return {
                "content": msg.content,
                "tool_calls": tool_calls
            }
        except Exception as e:
            logger.error(f"OpenAI chat_with_tools failed: {e}")
            raise

    async def structured_output(
        self,
        schema: Type[BaseModel],
        prompt: str,
        system_prompt: str,
        temperature: float = 0.1
    ) -> BaseModel:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=messages,
                response_format=schema,
                temperature=temperature
            )
            return response.choices[0].message.parsed
        except Exception as e:
            logger.error(f"OpenAI structured_output failed: {e}")
            raise

    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/ogg",
        prompt: Optional[str] = None
    ) -> Optional[str]:
        try:
            import io
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.ogg"
            transcription = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                prompt=prompt
            )
            return transcription.text.strip()
        except Exception as e:
            logger.error(f"OpenAI transcription failed: {e}")
            return None


def get_llm_adapter() -> Optional[LLMInterface]:
    """Factory to instantiate the configured adapter based on environment variables.
    Fails loudly if provider is specified but credentials/model are missing."""
    provider = (settings.LLM_PROVIDER or "auto").lower()

    # 1. Gemini
    if provider == "gemini" or (provider == "auto" and settings.GEMINI_API_KEY):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set but LLM_PROVIDER is 'gemini'. Cannot start assistant.")
        model = settings.LLM_MODEL or settings.GEMINI_MODEL or "gemini-2.5-flash"
        logger.info(f"Initialized Gemini LLM adapter with model: {model}")
        return GeminiAdapter(api_key=settings.GEMINI_API_KEY, model_name=model)

    # 2. OpenAI / OpenAI-compatible
    if provider == "openai" or (provider == "auto" and settings.OPENAI_API_KEY):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set but LLM_PROVIDER is 'openai'. Cannot start assistant.")
        model = settings.LLM_MODEL or settings.OPENAI_MODEL or "gpt-4o-mini"
        base_url = settings.OPENAI_BASE_URL or None
        logger.info(f"Initialized OpenAI-compatible LLM adapter with model: {model} (base_url: {base_url})")
        return OpenAICompatibleAdapter(api_key=settings.OPENAI_API_KEY, model_name=model, base_url=base_url)

    logger.warning("No live LLM API keys configured. Running with fallback mode.")
    return None

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

class LLMServiceWrapper:
    """Wrapper providing backward compatibility for existing callers (e.g. journal extraction)
    while routing through the unified LLMInterface adapter."""
    def __init__(self):
        self.adapter = get_llm_adapter()

    async def extract_journal_intelligence(self, raw_text: str, date_str: str):
        from ..schemas.journal import ExtractedJournalIntelligence
        if self.adapter:
            try:
                system_prompt = "You are an intelligent extraction engine for a personal Command Centre and Life OS."
                prompt = f"Analyze the following journal entry for date {date_str}:\n{raw_text}"
                return await self.adapter.structured_output(
                    schema=ExtractedJournalIntelligence,
                    prompt=prompt,
                    system_prompt=system_prompt
                )
            except Exception as e:
                logger.warning(f"Structured extraction via adapter failed: {e}. Falling back to rule extraction.")
        
        return self._heuristic_extraction(raw_text, date_str)

    def _heuristic_extraction(self, raw_text: str, date_str: str):
        import re
        from ..schemas.journal import ExtractedJournalIntelligence, NutritionSummary, NutritionItem, ExtractedPerson
        if not raw_text or not raw_text.strip():
            return ExtractedJournalIntelligence(
                summary="Empty journal entry.",
                mood_tag="Neutral",
                tags=[]
            )

        lower_text = raw_text.lower()
        items: List[NutritionItem] = []
        found_foods = set()
        total_cals = 0
        total_p = 0.0
        total_c = 0.0
        total_f = 0.0

        sorted_foods = sorted(FOOD_DATABASE.keys(), key=len, reverse=True)
        for food_key in sorted_foods:
            if re.search(r'\b' + re.escape(food_key) + r'\b', lower_text):
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

        people: List[ExtractedPerson] = []
        meeting_matches = re.finditer(
            r'\b(?:met|met with|caught up with|coffee with|lunch with|dinner with|drinks with|talked with|talked to|called|chat with|meeting with|synced with)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            raw_text,
            re.IGNORECASE
        )
        seen_names = []
        for m in meeting_matches:
            name = m.group(1).strip()
            if name.lower() not in ("today", "yesterday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "morning", "afternoon", "evening", "lunch", "dinner"):
                if name not in seen_names:
                    seen_names.append(name)

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
                target_person = seen_names[-1]
            elif subj.lower() not in ("i", "we", "he", "she", "they", "it", "my", "today"):
                target_person = subj
                if target_person not in seen_names:
                    seen_names.append(target_person)

            if target_person:
                facts_by_person.setdefault(target_person, []).append(fact)

        for name in seen_names:
            sentence = ""
            for s in re.split(r'[.!?]+', raw_text):
                if re.search(r'\b' + re.escape(name) + r'\b', s):
                    sentence = s.strip()
                    break
            
            location = None
            loc_match = re.search(r'(?:at|in)\s+([A-Z][A-Za-z0-9\s&\'\.-]+?)(?:,|\.|\s+with|\s+to|\s+for|$)', sentence)
            if loc_match:
                candidate_loc = loc_match.group(1).strip()
                if len(candidate_loc) > 2 and candidate_loc.lower() not in ("the", "this", "that"):
                    location = candidate_loc

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

        sentences = [s.strip() for s in re.split(r'[.!?]+', raw_text) if len(s.strip()) > 5]
        summary = sentences[0] if sentences else raw_text[:120]
        if not summary.endswith("."):
            summary += "."

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

    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "voice.ogg", mime_type: str = "audio/ogg") -> Optional[str]:
        if self.adapter:
            return await self.adapter.transcribe(audio_bytes=audio_bytes, mime_type=mime_type)
        return None

llm_service = LLMServiceWrapper()
llm_adapter = llm_service.adapter

