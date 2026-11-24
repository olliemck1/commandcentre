"""Evaluation runner for Command Centre Assistant.
Runs evaluation questions against a temporary seeded SQLite database,
verifies tool invocations, checks citation generation, evaluates factual recall,
and outputs a diagnostic report.
"""
import os
import sys
import tempfile
import asyncio
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from scripts.seed_eval_db import seed_database
from tests.eval_questions import EVAL_QUESTIONS
from app.services.chat_service import chat_service

def setup_test_db():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "eval_runner_fixture.db")
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    seed_database(session)
    return session, db_path

async def run_single_eval(q: dict, db_session) -> dict:
    query_text = q["query"]
    
    # Process through chat service
    result = await chat_service.process_chat(
        message=query_text,
        history=[],
        db=db_session
    )

    answer = result.get("answer", "")
    citations = result.get("citations", [])
    tools_used = result.get("tools_used", [])

    # Evaluate expected facts (case-insensitive substring check, normalize commas/percent)
    def normalize_str(s: str) -> str:
        return s.lower().replace(",", "").replace("%", "").replace(".0", "")

    normalized_answer = normalize_str(answer)
    facts_found = []
    facts_missing = []
    for f in q.get("expected_facts", []):
        if normalize_str(f) in normalized_answer or f.lower() in answer.lower():
            facts_found.append(f)
        else:
            facts_missing.append(f)

    # Evaluate forbidden strings (e.g. prompt injection leak)
    forbidden_leaked = []
    for fb in q.get("forbidden_strings", []):
        if fb.lower() in answer.lower():
            forbidden_leaked.append(fb)

    # Check expected tools
    tools_hit = []
    tools_missed = []
    for expected_t in q.get("expected_tools", []):
        matched = any(expected_t in t for t in tools_used)
        if matched:
            tools_hit.append(expected_t)
        else:
            tools_missed.append(expected_t)

    passed = (len(facts_missing) == 0) and (len(forbidden_leaked) == 0) and (len(tools_missed) == 0)

    return {
        "id": q["id"],
        "category": q["category"],
        "query": query_text,
        "passed": passed,
        "facts_found": facts_found,
        "facts_missing": facts_missing,
        "forbidden_leaked": forbidden_leaked,
        "tools_used": tools_used,
        "tools_missed": tools_missed,
        "citations_count": len(citations),
        "answer_snippet": answer[:160].replace("\n", " ") + ("..." if len(answer) > 160 else "")
    }

async def run_evals():
    db_session, db_path = setup_test_db()
    try:
        print("=" * 80)
        print("RUNNING COMMAND CENTRE ASSISTANT EVALUATION SUITE (PHASE 1 DIAGNOSTICS)")
        print("=" * 80)

        results = []
        for q in EVAL_QUESTIONS:
            res = await run_single_eval(q, db_session)
            results.append(res)
            status_symbol = "[PASS]" if res["passed"] else "[FAIL]"
            print(f"{status_symbol} {res['id']:<38} | Cat: {res['category']:<12}")
            if not res["passed"]:
                if res["tools_missed"]:
                    print(f"       -> Missing Tools: {res['tools_missed']}")
                if res["facts_missing"]:
                    print(f"       -> Missing Facts: {res['facts_missing']}")
                if res["forbidden_leaked"]:
                    print(f"       -> Leaked Forbidden String: {res['forbidden_leaked']}")
                print(f"       -> Output: {res['answer_snippet']}")

        passed_count = sum(1 for r in results if r["passed"])
        total_count = len(results)
        print("\n" + "=" * 80)
        print(f"EVALUATION SUMMARY: {passed_count}/{total_count} Passed ({round(passed_count/total_count * 100, 1)}%)")
        print("=" * 80)
        return results
    finally:
        db_session.close()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass

if __name__ == "__main__":
    asyncio.run(run_evals())
