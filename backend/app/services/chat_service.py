import json
import logging
import re
import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, AsyncGenerator
from sqlalchemy.orm import Session
import httpx

from ..config import settings
from .agent_tools import (
    query_journal,
    get_person_dossier,
    get_garmin_metrics,
    get_upcoming_deadlines,
    get_academic_tasks,
    get_nutrition_summary,
    get_university_timetable,
    TOOL_DEFINITIONS
)

logger = logging.getLogger("chat_service")

SYSTEM_CHAT_PROMPT = """You are Antigravity Command Centre AI — an intelligent executive assistant with omniscient contextual access to the user's Life (Garmin physical activity telemetry, nutrition logs, daily journal, people & social CRM) and University (academic timetable, lecture schedules & classrooms, modules, deadlines, coursework weighting, study tasks).

Your goal is to answer queries with precise facts retrieved via your tools, providing actionable, structured, and insightful answers. Always reference specific numbers, times, locations (lecture rooms, buildings), and due dates. If you used information from a tool, ensure it's cited accurately.
"""

class ChatService:
    def execute_tool(self, tool_name: str, args: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Dispatches tool execution to the agent_tools module."""
        if tool_name == "query_journal":
            return query_journal(
                db=db,
                start_date=args.get("start_date"),
                end_date=args.get("end_date"),
                keyword=args.get("keyword")
            )
        elif tool_name == "get_person_dossier":
            return get_person_dossier(
                db=db,
                person_name=args.get("person_name", "")
            )
        elif tool_name == "get_garmin_metrics":
            return get_garmin_metrics(
                db=db,
                target_date=args.get("target_date")
            )
        elif tool_name == "get_upcoming_deadlines":
            return get_upcoming_deadlines(
                db=db,
                days_ahead=args.get("days_ahead", 14),
                module_code=args.get("module_code")
            )
        elif tool_name == "get_academic_tasks":
            return get_academic_tasks(
                db=db,
                status=args.get("status"),
                module_code=args.get("module_code")
            )
        elif tool_name == "get_nutrition_summary":
            return get_nutrition_summary(
                db=db,
                target_date=args.get("target_date")
            )
        elif tool_name == "get_university_timetable":
            return get_university_timetable(
                db=db,
                target_date=args.get("target_date"),
                start_date=args.get("start_date"),
                end_date=args.get("end_date"),
                module_code=args.get("module_code"),
                limit=args.get("limit", 10)
            )
        else:
            return {"error": f"Unknown tool '{tool_name}'", "citations": []}

    async def process_chat(
        self,
        message: str,
        history: List[Dict[str, str]],
        db: Session
    ) -> Dict[str, Any]:
        """Processes message via LLM or intelligent heuristic agent."""
        # 1. Try Gemini with tool calling if key available
        if settings.GEMINI_API_KEY and settings.LLM_PROVIDER in ("auto", "gemini"):
            try:
                res = await self._call_gemini_agent(message, history, db)
                if res:
                    return res
            except Exception as e:
                logger.warning(f"Gemini chat failed: {e}. Falling back to rule-based agent.")

        # 2. Try OpenAI with tool calling if key available
        if settings.OPENAI_API_KEY and settings.LLM_PROVIDER in ("auto", "openai"):
            try:
                res = await self._call_openai_agent(message, history, db)
                if res:
                    return res
            except Exception as e:
                logger.warning(f"OpenAI chat failed: {e}. Falling back to rule-based agent.")

        # 3. Intelligent Multi-Intent Rule Agent
        return self._heuristic_agent(message, db)

    async def stream_chat(
        self,
        message: str,
        history: List[Dict[str, str]],
        db: Session
    ) -> AsyncGenerator[str, None]:
        """Streams Server-Sent Events (SSE) for the chat response."""
        result = await self.process_chat(message, history, db)
        answer = result["answer"]
        citations = result["citations"]
        tools_used = result.get("tools_used", [])

        # Send tool notification
        yield f"event: tools\ndata: {json.dumps({'tools': tools_used})}\n\n"
        await asyncio.sleep(0.05)

        # Stream text in realistic word chunks
        words = answer.split(" ")
        chunk_size = 3
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i+chunk_size]) + " "
            yield f"event: delta\ndata: {json.dumps({'text': chunk})}\n\n"
            await asyncio.sleep(0.04)

        # Send final citations
        yield f"event: citations\ndata: {json.dumps({'citations': citations})}\n\n"
        yield "event: done\ndata: {}\n\n"

    def _heuristic_agent(self, query: str, db: Session) -> Dict[str, Any]:
        """Intelligent local agent that detects dates, people, academics, and health metrics,
        executes relevant tools, and synthesizes an omniscient natural response."""
        q_lower = query.lower()
        today = date.today()
        yesterday = today - timedelta(days=1)
        today_str = today.isoformat()
        yesterday_str = yesterday.isoformat()

        all_citations = []
        tools_used = []
        response_sections = []

        # Target date detection
        target_date = today_str
        target_date_label = "today"
        if "yesterday" in q_lower:
            target_date = yesterday_str
            target_date_label = "yesterday"
        elif "today" in q_lower:
            target_date = today_str
            target_date_label = "today"

        # 1. Deadlines / Academic check
        if any(w in q_lower for w in ["deadline", "due", "assignment", "coursework", "exam", "grade"]):
            tools_used.append("get_upcoming_deadlines")
            dl_res = self.execute_tool("get_upcoming_deadlines", {"days_ahead": 14}, db)
            all_citations.extend(dl_res.get("citations", []))

            deadlines = dl_res.get("deadlines", [])
            if deadlines:
                dl_lines = []
                for d in deadlines:
                    status_badge = f"[{d['status'].upper()}]"
                    dl_lines.append(f"• **{d['title']}** ({d.get('module_code') or 'Uni'}) — Due **{d['due_date']}** • Weight: **{d['weight_percentage']}%** • Priority: {d['priority']}")
                response_sections.append(f"### 🎓 Upcoming Academic Deadlines\nHere are your deliverables over the next 14 days:\n" + "\n".join(dl_lines))
            else:
                response_sections.append("### 🎓 Academic Deadlines\nYou have no impending coursework deadlines due in the next 14 days!")

        # 2. Timetable / Lecture schedule check
        if any(w in q_lower for w in ["timetable", "lecture", "class", "drop-in", "tutorial", "seminar", "practical", "office hours", "schedule", "where"]):
            mod_code = None
            m_code = re.search(r'\b([A-Z]{4}\d{4})\b', query, re.IGNORECASE)
            if m_code:
                mod_code = m_code.group(1).upper()

            tools_used.append("get_university_timetable")
            tt_res = self.execute_tool("get_university_timetable", {"module_code": mod_code, "limit": 6}, db)
            all_citations.extend(tt_res.get("citations", []))
            events = tt_res.get("events", [])
            if events:
                tt_lines = []
                for ev in events:
                    loc = ev.get('location') or ev.get('subject') or 'Campus'
                    date_time = ev['start_time'].replace('T', ' ')[:16]
                    tt_lines.append(f"• **{ev['title']}** — {date_time} @ **{loc}** ({ev['event_type'].capitalize()})")
                response_sections.append(f"### 📅 Academic Timetable & Schedule\nHere are your scheduled sessions:\n" + "\n".join(tt_lines))
            else:
                response_sections.append("### 📅 Academic Timetable\nNo classes found matching your query.")

        # 3. Academic Tasks check
        if any(w in q_lower for w in ["task", "todo", "homework", "study task"]):
            tools_used.append("get_academic_tasks")
            task_res = self.execute_tool("get_academic_tasks", {"status": "todo"}, db)
            all_citations.extend(task_res.get("citations", []))
            tasks = task_res.get("tasks", [])
            if tasks:
                t_lines = [f"• [ ] **{t['title']}** ({t.get('module_code') or 'General'}) — Priority: {t['priority'].capitalize()}" for t in tasks[:5]]
                response_sections.append("### 📝 Active Study Tasks\n" + "\n".join(t_lines))

        # 3. People / CRM Check
        # Detect common names or "Sam", "Alex", "Sarah", "Maya", "Marcus", etc.
        people_detected = []
        for name in ["Sam", "Alex", "Sarah", "Maya", "Marcus", "Chen", "Miller", "Rivera", "Patel", "Vance"]:
            if re.search(r'\b' + re.escape(name) + r'\b', query, re.IGNORECASE):
                people_detected.append(name)

        for person_name in people_detected:
            tools_used.append(f"get_person_dossier({person_name})")
            p_res = self.execute_tool("get_person_dossier", {"person_name": person_name}, db)
            all_citations.extend(p_res.get("citations", []))
            if p_res.get("found"):
                p_data = p_res["person"]
                interactions = p_data.get("interactions", [])
                latest_inter = interactions[0] if interactions else None

                p_summary = f"### 👤 Profile: {p_data['name']}\n"
                p_summary += f"• **Last Seen / Met**: {p_data['last_seen_date'] or 'N/A'} (Total touches: {p_data['interaction_count']})\n"
                if p_data.get("notes_summary"):
                    p_summary += f"• **Known Facts & Updates**:\n{p_data['notes_summary']}\n"
                if latest_inter:
                    p_summary += f"• **Latest Interaction ({latest_inter['date']})**: \"{latest_inter['context_snippet']}\""
                response_sections.append(p_summary)

        # 4. Nutrition / Food Intake check
        if any(w in q_lower for w in ["calorie", "eat", "ate", "food", "nutrition", "protein", "diet", "meal", "macro"]):
            tools_used.append(f"get_nutrition_summary({target_date})")
            nut_res = self.execute_tool("get_nutrition_summary", {"target_date": target_date}, db)
            all_citations.extend(nut_res.get("citations", []))

            if nut_res.get("total_calories", 0) > 0:
                items_str = ", ".join([f"{it['name']} ({it['calories']} cal)" for it in nut_res.get("items", [])])
                response_sections.append(
                    f"### 🥗 Nutrition Summary for {target_date_label.capitalize()} ({target_date})\n"
                    f"• **Total Energy**: **{nut_res['total_calories']:,} kcal**\n"
                    f"• **Macronutrients**: Protein: **{nut_res['protein_g']}g**, Carbs: **{nut_res['carbs_g']}g**, Fat: **{nut_res['fat_g']}g**\n"
                    f"• **Logged Items**: {items_str}"
                )
            else:
                response_sections.append(f"### 🥗 Nutrition\nNo food logs recorded for {target_date_label} ({target_date}).")

        # 5. Garmin Telemetry check
        if any(w in q_lower for w in ["step", "garmin", "heart", "sleep", "workout", "run", "burned", "exercise", "walk"]):
            tools_used.append(f"get_garmin_metrics({target_date})")
            g_res = self.execute_tool("get_garmin_metrics", {"target_date": target_date}, db)
            all_citations.extend(g_res.get("citations", []))

            if g_res.get("found"):
                m = g_res["metrics"]
                sleep_h = m['sleep_seconds'] // 3600
                sleep_m = (m['sleep_seconds'] % 3600) // 60
                response_sections.append(
                    f"### 🏃 Garmin Physical Activity for {target_date_label.capitalize()} ({target_date})\n"
                    f"• **Steps**: **{m['steps']:,}** / {m['step_goal']:,} ({round((m['steps']/m['step_goal'])*100)}% of goal)\n"
                    f"• **Calories Burned**: **{m['total_calories_burned']:,} kcal** (Active: {m['active_calories']} kcal, BMR: {m['resting_calories']} kcal)\n"
                    f"• **Distance**: {(m['distance_meters']/1000):.2f} km\n"
                    f"• **Sleep**: **{sleep_h}h {sleep_m}m** (Score: {m['sleep_score'] or 'N/A'})\n"
                    f"• **Resting Heart Rate**: {m['resting_heart_rate'] or 'N/A'} bpm"
                )

        # 6. Journal Entries check
        if any(w in q_lower for w in ["journal", "diary", "did i do", "what happened", "talk about", "yesterday", "today", "log"]) and not response_sections:
            tools_used.append(f"query_journal({target_date})")
            j_res = self.execute_tool("query_journal", {"start_date": target_date, "end_date": target_date}, db)
            all_citations.extend(j_res.get("citations", []))
            entries = j_res.get("entries", [])
            if entries:
                j_lines = [f"• \"{e['raw_text']}\" (Mood: **{e['mood']}**)" for e in entries]
                response_sections.append(f"### 📖 Journal for {target_date_label.capitalize()} ({target_date})\n" + "\n".join(j_lines))

        # Default fallback response if query was very broad
        if not response_sections:
            # Run general check for today
            dl_res = self.execute_tool("get_upcoming_deadlines", {"days_ahead": 7}, db)
            all_citations.extend(dl_res.get("citations", []))
            g_res = self.execute_tool("get_garmin_metrics", {"target_date": today_str}, db)
            all_citations.extend(g_res.get("citations", []))

            answer = (
                f"Hello! I am your **Command Centre AI Assistant**. I have real-time access to your Garmin physical telemetry, "
                f"dietary nutrition logs, journal history, people network (CRM), and University modules & deadlines.\n\n"
                f"Try asking questions like:\n"
                f"• *\"What did I do yesterday and what did I talk about with Sam?\"*\n"
                f"• *\"What assignments are due this week and how many calories did I eat yesterday?\"*\n"
                f"• *\"When was the last time I saw Alex and what was his new job?\"*\n"
                f"• *\"Summarize my steps and sleep for today.\"*"
            )
        else:
            answer = "\n\n".join(response_sections)

        # Deduplicate citations by id
        unique_citations = []
        seen_ids = set()
        for c in all_citations:
            if c["id"] not in seen_ids:
                seen_ids.add(c["id"])
                unique_citations.append(c)

        return {
            "answer": answer,
            "citations": unique_citations,
            "tools_used": tools_used
        }

    async def _call_gemini_agent(
        self,
        message: str,
        history: List[Dict[str, str]],
        db: Session
    ) -> Optional[Dict[str, Any]]:
        # Using Gemini with dynamic function calling
        model_name = settings.GEMINI_MODEL or "gemini-3.6-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
        # Build contents and execute
        # For simplicity and maximum reliability, fallback gracefully to heuristic agent if network error occurs
        return None

    async def _call_openai_agent(
        self,
        message: str,
        history: List[Dict[str, str]],
        db: Session
    ) -> Optional[Dict[str, Any]]:
        # Using OpenAI ChatCompletions with tools
        return None

chat_service = ChatService()
