import os
import sys
import json
import threading
from datetime import datetime, timezone

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.buyer.property_store import PropertyStore
from src.buyer.property_scoring import calculate_home_score, passes_hard_filters
from src.buyer.search_config import DEFAULT_HOME_SEARCH

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "buyer.db")
SEARCH_NAME = "antwerp-home"

st.set_page_config(page_title="Immowbot Buyer", layout="wide")


@st.cache_resource
def get_store():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    store = PropertyStore(DB_PATH)
    store.save_search(SEARCH_NAME, "home", DEFAULT_HOME_SEARCH)
    return store


def _search_id(store):
    searches = store.list_searches()
    for s in searches:
        if s["name"] == SEARCH_NAME:
            return s["id"]
    return None


def _last_runs(store, search_id, n=5):
    rows = store.connection.execute(
        """SELECT r.id, r.started_at, r.completed_at, r.status,
                  GROUP_CONCAT(sr.source || ':' || sr.status || ':' || sr.listing_count, '|') as sources
           FROM runs r
           LEFT JOIN source_runs sr ON sr.run_id = r.id
           WHERE r.search_id = ?
           GROUP BY r.id
           ORDER BY r.id DESC
           LIMIT ?""",
        (search_id, n),
    ).fetchall()
    return [dict(r) for r in rows]


def _run_collection_thread(store_path, search_id):
    from src.buyer.property_store import PropertyStore
    from src.buyer.collector import run_collection
    from src.scraper_manager import ScraperManager

    store = PropertyStore(store_path)
    manager = ScraperManager()
    try:
        run_collection(store, search_id, manager)
    finally:
        store.close()


def _score_and_filter(listings, config):
    results = []
    for listing in listings:
        result = calculate_home_score(listing, config)
        results.append({**listing, "_score": result["score"], "_components": result["components"], "_exclusions": result["exclusions"]})
    results.sort(key=lambda x: (x["_score"] is None, -(x["_score"] or 0)))
    return results


def _fmt_price(price):
    if price is None:
        return "—"
    return f"€{int(price):,}".replace(",", ".")


def _fmt_score(score):
    if score is None:
        return "—"
    return f"{score:.1f}"


def _epc_badge(epc):
    colors = {"A++": "#00a651", "A+": "#00a651", "A": "#00a651", "B": "#79b830", "C": "#c8d200",
              "D": "#f0a500", "E": "#e57200", "F": "#c00000", "G": "#8b0000"}
    color = colors.get(epc, "#888")
    return f'<span style="background:{color};color:white;padding:2px 6px;border-radius:3px;font-weight:bold">{epc or "?"}</span>'


def main():
    store = get_store()
    search_id = _search_id(store)
    config = store.get_search(search_id)["config"]

    st.title("Immowbot Buyer Dashboard")

    # --- Sidebar ---
    with st.sidebar:
        st.header("Search config")
        st.write(f"**Postcodes:** {', '.join(config['postcodes'])}")
        st.write(f"**Max price:** {_fmt_price(config['max_price'])}")
        st.write(f"**Min surface:** {config['min_surface_area']} m²")
        st.write(f"**Min bedrooms:** {config['min_bedrooms']}")
        st.write(f"**EPC labels:** {', '.join(config['epc_labels'])}")
        st.write(f"**Portals:** {', '.join(config['portals'])}")
        st.divider()

        if "collecting" not in st.session_state:
            st.session_state.collecting = False

        if st.session_state.collecting:
            st.info("Collection running in background...")
            if st.button("Refresh status"):
                st.session_state.collecting = False
                st.rerun()
        else:
            if st.button("Run collection", type="primary", use_container_width=True):
                st.session_state.collecting = True
                t = threading.Thread(
                    target=_run_collection_thread,
                    args=(os.path.abspath(DB_PATH), search_id),
                    daemon=True,
                )
                t.start()
                st.session_state._thread = t
                st.rerun()

        st.divider()
        st.caption(f"DB: {DB_PATH}")

    # --- Tabs ---
    tab_listings, tab_history = st.tabs(["Listings", "Run history"])

    with tab_listings:
        listings = store.latest_listings("sale")
        scored = _score_and_filter(listings, config)

        passing = [l for l in scored if l["_score"] is not None]
        excluded = [l for l in scored if l["_score"] is None]

        col1, col2, col3 = st.columns(3)
        col1.metric("Total in store", len(listings))
        col2.metric("Pass filters", len(passing))
        col3.metric("Excluded", len(excluded))

        if not passing:
            st.info("No listings pass the current filters. Run a collection first.")
        else:
            show_excluded = st.toggle("Show excluded listings", value=False)
            display_list = passing + (excluded if show_excluded else [])

            selected_url = st.session_state.get("selected_url")

            # Table
            rows = []
            for l in display_list:
                rows.append({
                    "Score": _fmt_score(l["_score"]),
                    "Price": _fmt_price(l.get("price")),
                    "Type": l.get("property_type", ""),
                    "Postcode": l.get("postcode", ""),
                    "m²": l.get("surface_area"),
                    "Beds": l.get("bedrooms"),
                    "EPC": l.get("epc_score", ""),
                    "Source": l.get("source", ""),
                    "_url": l.get("url", ""),
                })

            for i, (row, listing) in enumerate(zip(rows, display_list)):
                score_color = "#28a745" if listing["_score"] and listing["_score"] >= 60 else \
                              "#ffc107" if listing["_score"] and listing["_score"] >= 40 else "#dc3545"
                is_selected = selected_url == listing.get("url")
                border = "2px solid #1f77b4" if is_selected else "1px solid #dee2e6"

                with st.container():
                    cols = st.columns([1, 2, 1.5, 1, 1, 1, 1, 1.5, 1])
                    score_html = f'<span style="color:{score_color};font-weight:bold">{_fmt_score(listing["_score"])}</span>'
                    cols[0].markdown(score_html, unsafe_allow_html=True)
                    cols[1].write(_fmt_price(listing.get("price")))
                    cols[2].write(listing.get("property_type", "").title())
                    cols[3].write(listing.get("postcode", ""))
                    cols[4].write(f"{listing.get('surface_area', '?')} m²")
                    cols[5].write(f"{listing.get('bedrooms', '?')} bd")
                    cols[6].markdown(_epc_badge(listing.get("epc_score")), unsafe_allow_html=True)
                    cols[7].write(listing.get("source", ""))
                    if cols[8].button("Detail", key=f"detail_{i}"):
                        if is_selected:
                            st.session_state.selected_url = None
                        else:
                            st.session_state.selected_url = listing.get("url")
                        st.rerun()

            # Detail panel
            selected_url = st.session_state.get("selected_url")
            if selected_url:
                selected = next((l for l in display_list if l.get("url") == selected_url), None)
                if selected:
                    st.divider()
                    _render_detail(selected)

    with tab_history:
        runs = _last_runs(store, search_id)
        if not runs:
            st.info("No runs yet.")
        else:
            for run in runs:
                started = run["started_at"][:19].replace("T", " ") if run["started_at"] else "?"
                completed = run["completed_at"][:19].replace("T", " ") if run["completed_at"] else "running"
                status_icon = "✅" if run["status"] == "ok" else "⚠" if run["status"] == "partial" else "🔄"

                with st.expander(f"{status_icon} Run #{run['id']} — {started} → {completed}"):
                    sources_raw = run.get("sources") or ""
                    if sources_raw:
                        for part in sources_raw.split("|"):
                            bits = part.split(":")
                            if len(bits) == 3:
                                src, src_status, count = bits
                                icon = "✅" if src_status == "ok" else "❌"
                                st.write(f"{icon} **{src}**: {count} listings saved")


def _render_detail(listing):
    st.subheader(listing.get("name") or listing.get("url", ""))

    col1, col2 = st.columns([2, 1])
    with col1:
        info_cols = st.columns(4)
        info_cols[0].metric("Price", _fmt_price(listing.get("price")))
        info_cols[1].metric("Surface", f"{listing.get('surface_area', '?')} m²")
        info_cols[2].metric("Bedrooms", listing.get("bedrooms", "?"))
        info_cols[3].metric("EPC", listing.get("epc_score") or "?")

        score = listing.get("_score")
        components = listing.get("_components", {})
        if score is not None:
            st.write(f"**Score: {score:.1f} / 100**")
            comp_labels = {
                "price": "Price headroom (30)",
                "surface_area": "Surface area (25)",
                "bedrooms": "Bedrooms (15)",
                "epc": "EPC label (20)",
                "completeness": "Data completeness (10)",
            }
            for key, label in comp_labels.items():
                val = components.get(key, 0)
                max_val = int(label.split("(")[1].rstrip(")"))
                pct = val / max_val if max_val else 0
                st.write(f"{label}: **{val:.1f}**")
                st.progress(pct)
        else:
            exclusions = listing.get("_exclusions", [])
            st.warning(f"Excluded: {', '.join(exclusions) or 'fails hard filters'}")

        st.link_button("Open listing", listing.get("url", "#"))

    with col2:
        st.write("**Details**")
        for key in ("postcode", "property_type", "source", "construction_year"):
            val = listing.get(key)
            if val:
                st.write(f"- **{key.replace('_', ' ').title()}**: {val}")

        desc = listing.get("description_english") or listing.get("description", "")
        if desc:
            st.write("**Description**")
            st.caption(desc[:500] + ("..." if len(desc) > 500 else ""))


if __name__ == "__main__":
    main()
