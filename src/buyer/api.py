import asyncio
import hashlib
import hmac
import json
import os
import queue
import sqlite3
import sys
import threading
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from src.buyer.property_scoring import calculate_home_score
from src.buyer.purchase_calculator import calculate_purchase_estimate
from src.buyer.property_store import PropertyStore
from src.buyer.search_config import DEFAULT_HOME_SEARCH, normalize_search_config
from src.buyer.smart_lists import BUILTIN_SMART_LISTS, matches_rule
from src.buyer.change_tracking import diff_versions

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "buyer.db"))
SEARCH_NAME = "antwerp-home"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

AUTH_USER = os.getenv("IMMOWBOT_USER", "admin")
AUTH_PASSWORD = os.getenv("IMMOWBOT_PASSWORD", "change-me")
AUTH_SECRET = os.getenv("IMMOWBOT_AUTH_SECRET", "change-me-in-production")
AUTH_COOKIE = "immowbot_session"


def _session_token():
    payload = f"{AUTH_USER}:{int(time.time()) // 86400}"
    signature = hmac.new(AUTH_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def _valid_session(token):
    if not token:
        return False
    try:
        user, day, signature = token.split(":", 2)
        payload = f"{user}:{day}"
        expected = hmac.new(AUTH_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return user == AUTH_USER and int(day) >= int(time.time()) // 86400 - 1 and hmac.compare_digest(signature, expected)
    except (ValueError, TypeError):
        return False


@app.middleware("http")
async def require_login(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.url.path not in {"/api/auth/login", "/api/auth/me"}:
        if not _valid_session(request.cookies.get(AUTH_COOKIE)):
            return JSONResponse({"detail": "Authentication required"}, status_code=401)
    return await call_next(request)


@app.post("/api/auth/login")
async def login(body: dict):
    user = str(body.get("username") or "")
    password = str(body.get("password") or "")
    if not hmac.compare_digest(user, AUTH_USER) or not hmac.compare_digest(password, AUTH_PASSWORD):
        raise HTTPException(401, "Invalid username or password")
    response = JSONResponse({"username": AUTH_USER})
    response.set_cookie(AUTH_COOKIE, _session_token(), httponly=True, samesite="lax", secure=False, max_age=172800)
    return response


@app.get("/api/auth/me")
async def auth_me(request: Request):
    if not _valid_session(request.cookies.get(AUTH_COOKIE)):
        raise HTTPException(401, "Authentication required")
    return {"username": AUTH_USER}


@app.post("/api/auth/logout")
async def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(AUTH_COOKIE)
    return response

_state = {"search_id": None, "collection": None}


def get_store():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return PropertyStore(DB_PATH)


@app.on_event("startup")
def startup():
    store = get_store()
    try:
        existing = store.get_search_by_name(SEARCH_NAME)
        if existing:
            config = {**DEFAULT_HOME_SEARCH, **existing["config"]}
            _state["search_id"] = store.save_search(SEARCH_NAME, existing["purpose"], config)
        else:
            _state["search_id"] = store.save_search(SEARCH_NAME, "home", DEFAULT_HOME_SEARCH)
        store.ensure_builtin_smart_lists(BUILTIN_SMART_LISTS)
    finally:
        store.close()


@app.get("/api/listings")
def get_listings():
    store = get_store()
    try:
        config = store.get_search(_state["search_id"])["config"]
        listings = store.latest_listings("sale")
        all_notes = store.get_all_notes()
        result = []
        for listing in listings:
            scored = calculate_home_score(listing, config)
            src = listing.get("source", "")
            lid = str(listing.get("source_listing_id", ""))
            list_ids = list(store.get_property_list_ids(src, lid))
            note = all_notes.get((src, lid), "")
            result.append({
                **listing,
                "_score": scored["score"],
                "_components": scored["components"],
                "_score_weights": config.get("score_weights"),
                "_exclusions": scored["exclusions"],
                "_list_ids": list_ids,
                "_note": note,
                "_purchase_estimate": calculate_purchase_estimate(listing, config),
            })
        result.sort(key=lambda x: (x["_score"] is None, -(x["_score"] or 0)))
        return result
    finally:
        store.close()


@app.get("/api/config")
def get_config():
    store = get_store()
    try:
        return store.get_search(_state["search_id"])["config"]
    finally:
        store.close()


@app.put("/api/config")
def update_config(body: dict):
    store = get_store()
    try:
        current = store.get_search(_state["search_id"])["config"]
        merged = {**current, **body}
        try:
            normalize_search_config(merged)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        _state["search_id"] = store.save_search(SEARCH_NAME, "home", merged)
        return store.get_search(_state["search_id"])["config"]
    finally:
        store.close()


@app.get("/api/runs")
def get_runs():
    store = get_store()
    try:
        rows = store.connection.execute(
            """SELECT r.id, r.started_at, r.completed_at, r.status,
                      GROUP_CONCAT(sr.source || ':' || sr.status || ':' || sr.listing_count, '|') as sources_raw
               FROM runs r
               LEFT JOIN source_runs sr ON sr.run_id = r.id
               WHERE r.search_id = ?
               GROUP BY r.id
               ORDER BY r.id DESC
               LIMIT 20""",
            (_state["search_id"],),
        ).fetchall()
        runs = []
        for row in rows:
            sources = []
            if row["sources_raw"]:
                for part in row["sources_raw"].split("|"):
                    bits = part.split(":")
                    if len(bits) == 3:
                        sources.append({"source": bits[0], "status": bits[1], "count": int(bits[2])})
            runs.append({
                "id": row["id"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "status": row["status"],
                "sources": sources,
            })
        return runs
    finally:
        store.close()


@app.get("/api/runs/stream")
async def stream_progress():
    async def generator():
        while True:
            col = _state.get("collection")
            if col and col["thread"].is_alive():
                while True:
                    try:
                        col["progress"].update(col["progress_queue"].get_nowait())
                    except queue.Empty:
                        break
                p = col["progress"]
                yield {"data": json.dumps({
                    "alive": True,
                    "checked": p.get("checked", 0),
                    "saved": p.get("saved", 0),
                    "portal": p.get("portal", ""),
                    "cancelling": col["cancel_event"].is_set(),
                })}
            else:
                if col:
                    while True:
                        try:
                            col["progress"].update(col["progress_queue"].get_nowait())
                        except queue.Empty:
                            break
                    p = col["progress"]
                    _state["collection"] = None
                    yield {"data": json.dumps({
                        "alive": False,
                        "status": p.get("status", "ok"),
                        "checked": p.get("checked", 0),
                        "saved": p.get("saved", 0),
                        "error": p.get("error"),
                    })}
                else:
                    yield {"data": json.dumps({"alive": False})}
            await asyncio.sleep(0.8)
    return EventSourceResponse(generator())


@app.delete("/api/runs/active")
def cancel_run():
    col = _state.get("collection")
    if col and col["thread"].is_alive():
        col["cancel_event"].set()
        return {"ok": True}
    return {"ok": False}


@app.post("/api/runs")
def start_run():
    if _state.get("collection") and _state["collection"]["thread"].is_alive():
        raise HTTPException(409, "Collection already running")
    store = get_store()
    try:
        search = store.get_search_by_name(SEARCH_NAME)
        if not search:
            raise HTTPException(500, "Search configuration is unavailable")
        search_id = search["id"]
    finally:
        store.close()

    def _worker(store_path, search_id, cancel_event, progress_queue):
        from src.buyer.collector import run_collection
        from src.scraper_manager import ScraperManager
        store = PropertyStore(store_path)
        manager = ScraperManager()
        try:
            run_id = run_collection(
                store, search_id, manager,
                on_progress=progress_queue.put,
                should_cancel=cancel_event.is_set,
            )
            progress_queue.put({"status": store.get_run(run_id)["status"]})
        except Exception as exc:
            progress_queue.put({"status": "error", "error": str(exc)})
        finally:
            store.close()

    cancel_event = threading.Event()
    progress_queue = queue.Queue()
    thread = threading.Thread(
        target=_worker,
        args=(DB_PATH, search_id, cancel_event, progress_queue),
        daemon=True,
    )
    _state["collection"] = {
        "thread": thread,
        "cancel_event": cancel_event,
        "progress_queue": progress_queue,
        "progress": {"checked": 0, "saved": 0, "status": "running"},
    }
    thread.start()
    return {"ok": True}


@app.get("/api/runs/{run_id}/listings")
def get_run_listings(run_id: int):
    store = get_store()
    try:
        return store.listings_for_run(run_id)
    finally:
        store.close()


@app.get("/api/lists")
def get_lists():
    store = get_store()
    try:
        return store.get_lists()
    finally:
        store.close()


@app.post("/api/lists")
def create_list(body: dict):
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "name required")
    store = get_store()
    try:
        list_id = store.create_list(name)
        return {"id": list_id, "name": name}
    finally:
        store.close()


@app.delete("/api/lists/{list_id}")
def delete_list(list_id: int):
    store = get_store()
    try:
        store.delete_list(list_id)
        return {"ok": True}
    finally:
        store.close()


@app.get("/api/lists/{list_id}/items")
def get_list_items(list_id: int):
    store = get_store()
    try:
        return store.get_list_items(list_id)
    finally:
        store.close()


@app.post("/api/lists/{list_id}/items")
def add_to_list(list_id: int, body: dict):
    source = body.get("source", "")
    sid = str(body.get("source_listing_id", ""))
    if not source or not sid:
        raise HTTPException(400, "source and source_listing_id required")
    store = get_store()
    try:
        store.add_to_list(list_id, source, sid)
        return {"ok": True}
    finally:
        store.close()


@app.delete("/api/lists/{list_id}/items/{source}/{source_listing_id}")
def remove_from_list(list_id: int, source: str, source_listing_id: str):
    store = get_store()
    try:
        store.remove_from_list(list_id, source, source_listing_id)
        return {"ok": True}
    finally:
        store.close()


@app.get("/api/notes/{source}/{source_listing_id}")
def get_note(source: str, source_listing_id: str):
    store = get_store()
    try:
        return {"note": store.get_note(source, source_listing_id)}
    finally:
        store.close()


@app.put("/api/notes/{source}/{source_listing_id}")
def save_note(source: str, source_listing_id: str, body: dict):
    note = body.get("note", "")
    store = get_store()
    try:
        store.save_note(source, source_listing_id, note)
        return {"ok": True}
    finally:
        store.close()


@app.delete("/api/listings/{source}/{source_listing_id}")
def delete_listing(source: str, source_listing_id: str):
    store = get_store()
    try:
        store.delete_listing(source, source_listing_id)
        return {"ok": True}
    finally:
        store.close()


@app.get("/api/changes/{source}/{source_listing_id}")
def get_listing_changes(source: str, source_listing_id: str):
    store = get_store()
    try:
        history = store.listing_history(source, source_listing_id)
        changes = []
        for index in range(1, len(history)):
            for change in diff_versions(history[index - 1]["payload"], history[index]["payload"]):
                changes.append({**change, "observed_at": history[index]["observed_at"]})
        return {"history": history, "changes": changes}
    finally:
        store.close()


def _smart_listing_results(store, rule):
    config = store.get_search(_state["search_id"])["config"]
    results = []
    for listing in store.latest_listings("sale"):
        scored = calculate_home_score(listing, config)
        purchase = calculate_purchase_estimate(listing, config)
        if matches_rule(listing, rule, scored["score"], purchase):
            results.append({**listing, "_score": scored["score"], "_purchase_estimate": purchase})
    return results


@app.get("/api/smart-lists")
def get_smart_lists():
    store = get_store()
    try:
        store.ensure_builtin_smart_lists(BUILTIN_SMART_LISTS)
        result = []
        for item in store.get_smart_lists():
            matches = _smart_listing_results(store, item["rule"]) if item["enabled"] else []
            result.append({**item, "item_count": len(matches)})
        return result
    finally:
        store.close()


@app.post("/api/smart-lists")
def create_smart_list(body: dict):
    try:
        name = (body.get("name") or "").strip()
        rule = body.get("rule") or {}
        store = get_store()
        try:
            list_id = store.create_smart_list(name, rule)
            return {"id": list_id, "name": name, "rule": rule, "enabled": True, "is_system": False}
        finally:
            store.close()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "smart list name already exists")
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.patch("/api/smart-lists/{list_id}")
def update_smart_list(list_id: int, body: dict):
    store = get_store()
    try:
        current = next((x for x in store.get_smart_lists() if x["id"] == list_id), None)
        if current is None:
            raise HTTPException(404, "smart list not found")
        ok = store.update_smart_list(list_id, body.get("name", current["name"]), body.get("rule", current["rule"]), body.get("enabled", current["enabled"]))
        return {"ok": ok}
    finally:
        store.close()


@app.delete("/api/smart-lists/{list_id}")
def delete_smart_list(list_id: int):
    store = get_store()
    try:
        try:
            if not store.delete_smart_list(list_id):
                raise HTTPException(404, "smart list not found")
        except ValueError as exc:
            raise HTTPException(409, str(exc))
        return {"ok": True}
    finally:
        store.close()


@app.get("/api/smart-lists/{list_id}/items")
def get_smart_list_items(list_id: int):
    store = get_store()
    try:
        current = next((x for x in store.get_smart_lists() if x["id"] == list_id), None)
        if current is None:
            raise HTTPException(404, "smart list not found")
        return _smart_listing_results(store, current["rule"]) if current["enabled"] else []
    finally:
        store.close()


_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.isdir(_dist):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=_dist, html=True), name="static")
