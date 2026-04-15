"""
test_pipeline.py — Integration tests for the Jojo Bot backend.

Run from src/backend with venv active:
    python test_pipeline.py
"""
import asyncio
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PASS = "✅"
FAIL = "❌"

SAMPLE_QUESTIONS = [
    "How do I prime the pumps on the ÄKTA pure?",
    "What causes high backpressure?",
    "How do I create a gradient method in UNICORN 7?",
    "What is the maintenance schedule for ÄKTA pure?",
    "How do I calibrate the pH electrode?",
]


def test_retriever():
    print("\n--- Testing Retriever ---")
    try:
        from rag.retriever import retrieve
        for q in SAMPLE_QUESTIONS:
            results = retrieve(q, k=3)
            status = PASS if results else FAIL
            print(f"  {status} '{q[:60]}...' → {len(results)} chunks")
        return True
    except RuntimeError as e:
        print(f"  {FAIL} Retriever error: {e}")
        return False
    except Exception as e:
        print(f"  {FAIL} Unexpected error: {e}")
        traceback.print_exc()
        return False


async def test_generator():
    print("\n--- Testing Generator ---")
    try:
        from rag.retriever import retrieve
        from rag.generator import generate

        query = SAMPLE_QUESTIONS[0]
        chunks = retrieve(query, k=3)
        result = await generate(query=query, chunks=chunks, history=[], use_web_search=False)

        has_response = bool(result.get("response"))
        has_citations = isinstance(result.get("citations"), list)

        print(f"  {PASS if has_response else FAIL} Response present: {has_response}")
        print(f"  {PASS if has_citations else FAIL} Citations list: {has_citations}")
        print(f"  Preview: {result['response'][:120]}...")
        return has_response
    except Exception as e:
        print(f"  {FAIL} Generator error: {e}")
        traceback.print_exc()
        return False


async def test_session_store():
    print("\n--- Testing Session Store ---")
    try:
        from db.database import init_db, AsyncSessionLocal
        from db.session_store import (
            create_session, get_session, add_message,
            get_history, delete_session, update_session_title
        )

        await init_db()
        async with AsyncSessionLocal() as db:
            # Create
            sid = await create_session(db, instrument_context="pure")
            print(f"  {PASS} Created session: {sid[:8]}...")

            # Get
            sess = await get_session(db, sid)
            print(f"  {PASS if sess else FAIL} Retrieved session: {bool(sess)}")

            # Add messages
            await add_message(db, sid, "user", "Test question?")
            await add_message(db, sid, "assistant", "Test answer!", citations=[])

            # Get history
            history = await get_history(db, sid, max_turns=6)
            print(f"  {PASS if len(history) == 2 else FAIL} History length: {len(history)}")

            # Update title
            await update_session_title(db, sid, "Test question — a longer message here")
            updated = await get_session(db, sid)
            print(f"  {PASS if updated and updated['title'] else FAIL} Title set: {updated.get('title') if updated else 'N/A'}")

            # Delete
            deleted = await delete_session(db, sid)
            print(f"  {PASS if deleted else FAIL} Deleted: {deleted}")

            gone = await get_session(db, sid)
            print(f"  {PASS if gone is None else FAIL} Confirmed deleted: {gone is None}")

        return True
    except Exception as e:
        print(f"  {FAIL} Session store error: {e}")
        traceback.print_exc()
        return False


async def test_health():
    print("\n--- Testing Health Endpoint (import only) ---")
    try:
        from main import app
        print(f"  {PASS} FastAPI app imported successfully")
        return True
    except Exception as e:
        print(f"  {FAIL} App import error: {e}")
        traceback.print_exc()
        return False


async def main():
    print("=" * 50)
    print("  Jojo Bot — Backend Pipeline Tests")
    print("=" * 50)

    results = []

    results.append(("Retriever", test_retriever()))

    gen_ok = await test_generator()
    results.append(("Generator", gen_ok))

    sess_ok = await test_session_store()
    results.append(("Session Store", sess_ok))

    health_ok = await test_health()
    results.append(("App Import", health_ok))

    print("\n" + "=" * 50)
    print("  Results")
    print("=" * 50)
    for name, ok in results:
        print(f"  {PASS if ok else FAIL} {name}")

    all_passed = all(ok for _, ok in results)
    print(f"\n{'All tests passed!' if all_passed else 'Some tests failed.'}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
