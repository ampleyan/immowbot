import os
import queue
import sys
import threading

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.buyer.property_scoring import calculate_home_score
from src.buyer.property_store import PropertyStore
from src.buyer.search_config import DEFAULT_HOME_SEARCH

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "buyer.db")
SEARCH_NAME = "antwerp-home"
USER_ID = 1

st.set_page_config(
    page_title="Immowbot",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

_EPC_COLORS = {
    "A++": "#006B3C", "A+": "#006B3C", "A": "#006B3C",
    "B": "#2D8A4E", "C": "#7AB648",
    "D": "#F5C400", "E": "#F0A500",
    "F": "#D93E1F", "G": "#9B1B0E",
}

_SCORE_COLOR = {
    "high": "#059669",
    "mid": "#D97706",
    "low": "#DC2626",
    "none": "#9CA3AF",
}


def _inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', system-ui, -apple-system, sans-serif !important;
    }

    /* ── Page ── */
    .stApp { background: #F2F4F7; }

    [data-testid="stMainBlockContainer"] {
        padding: 1.75rem 2.25rem 3rem;
        max-width: 1440px;
    }

    h1 {
        font-size: 1.3rem !important;
        font-weight: 600 !important;
        color: #101828 !important;
        letter-spacing: -0.02em !important;
        margin-bottom: 0.1rem !important;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: #1E1B4B !important;
        border-right: none !important;
    }
    [data-testid="stSidebarContent"] { padding: 1.25rem 1rem 1.5rem; }

    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] span:not([data-testid]),
    [data-testid="stSidebar"] small { color: #A5B4FC !important; }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #E0E7FF !important;
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        margin: 0.25rem 0 0.6rem !important;
    }

    [data-testid="stSidebar"] input[type="text"],
    [data-testid="stSidebar"] input[type="number"],
    [data-testid="stSidebar"] textarea {
        background: #2D2A6E !important;
        border: 1px solid #3730A3 !important;
        color: #E0E7FF !important;
        border-radius: 6px !important;
    }
    [data-testid="stSidebar"] input:focus { border-color: #818CF8 !important; }

    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="popover"] > div {
        background: #2D2A6E !important;
        border-color: #3730A3 !important;
    }
    [data-testid="stSidebar"] [data-baseweb="tag"] {
        background: #3730A3 !important;
        color: #C7D2FE !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: #2D2A6E !important;
        margin: 0.875rem 0 !important;
    }

    [data-testid="stSidebarCollapseButton"] button {
        background: #2D2A6E !important;
        color: #818CF8 !important;
        border: none !important;
        border-radius: 6px !important;
    }
    [data-testid="stSidebarCollapseButton"] button:hover {
        background: #3730A3 !important;
        color: #C7D2FE !important;
    }

    [data-testid="stSidebar"] .stCaption p {
        color: #6366F1 !important;
        font-size: 0.68rem !important;
    }

    /* ── Metrics ── */
    [data-testid="stMetric"] {
        background: white;
        border-radius: 10px;
        padding: 0.875rem 1.25rem 0.75rem;
        border: 1px solid #E4E7EC;
        box-shadow: 0 1px 3px rgba(16,24,40,0.05);
    }
    [data-testid="stMetricLabel"] p {
        font-size: 0.7rem !important;
        font-weight: 500 !important;
        color: #667085 !important;
        letter-spacing: 0.02em;
    }
    [data-testid="stMetricValue"] div {
        font-size: 1.65rem !important;
        font-weight: 600 !important;
        color: #101828 !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent !important;
        border-bottom: 1px solid #E4E7EC !important;
        gap: 0 !important;
        padding-bottom: 0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        color: #667085 !important;
        padding: 0.6rem 1.1rem !important;
        background: transparent !important;
        border-bottom: 2px solid transparent !important;
        margin-bottom: -1px !important;
    }
    .stTabs [aria-selected="true"] {
        color: #101828 !important;
        border-bottom: 2px solid #2D6BE4 !important;
        font-weight: 600 !important;
        background: transparent !important;
    }

    /* ── Buttons — base ── */
    .stButton > button[kind="primary"] {
        background: #2D6BE4 !important;
        color: white !important;
        border: none !important;
        border-radius: 7px !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        padding: 0.4rem 1rem !important;
        transition: background 0.15s !important;
    }
    .stButton > button[kind="primary"]:hover { background: #1D56C4 !important; }

    .stButton > button:not([kind="primary"]) {
        background: white !important;
        border: 1px solid #D0D5DD !important;
        border-radius: 7px !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        color: #344054 !important;
        padding: 0.3rem 0.75rem !important;
        transition: border-color 0.15s, background 0.15s !important;
    }
    .stButton > button:not([kind="primary"]):hover {
        border-color: #98A2B3 !important;
        background: #F9FAFB !important;
    }

    /* ── Sidebar buttons ── */
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: #4F46E5 !important;
        width: 100%;
    }
    [data-testid="stSidebar"] .stButton > button:not([kind="primary"]) {
        background: #2D2A6E !important;
        border-color: #3730A3 !important;
        color: #A5B4FC !important;
        width: 100%;
    }

    /* ── Link button ── */
    .stLinkButton a {
        background: #101828 !important;
        color: white !important;
        border: none !important;
        border-radius: 7px !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        padding: 0.4rem 1rem !important;
    }
    .stLinkButton a:hover { background: #1D2939 !important; }

    /* ── Expanders ── */
    .stExpander {
        background: white !important;
        border: 1px solid #E4E7EC !important;
        border-radius: 10px !important;
        margin-bottom: 0.5rem;
        box-shadow: 0 1px 3px rgba(16,24,40,0.04) !important;
    }
    .stExpander > details > summary {
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        color: #344054 !important;
        padding: 0.75rem 1rem !important;
    }

    /* ── Listing cards ── */
    [data-testid="stHorizontalBlock"]:has(.listing-row-anchor) {
        background: white;
        border-radius: 12px;
        border: 1px solid #E4E7EC;
        padding: 0.5rem 0.875rem !important;
        margin-bottom: 0.45rem;
        box-shadow: 0 1px 3px rgba(16,24,40,0.06);
        align-items: center !important;
        transition: box-shadow 0.15s, border-color 0.15s;
    }
    [data-testid="stHorizontalBlock"]:has(.listing-row-anchor):hover {
        box-shadow: 0 4px 14px rgba(16,24,40,0.10);
        border-color: #C8D3E6;
    }
    [data-testid="stHorizontalBlock"]:has(.listing-row-anchor):has(input[type="checkbox"]:checked) {
        border-color: #93C5FD;
        background: #F5F9FF;
        box-shadow: 0 0 0 1px #BFDBFE, 0 1px 3px rgba(16,24,40,0.06);
    }

    /* ── Detail panel ── */
    [data-testid="stHorizontalBlock"]:has(.detail-panel-anchor) {
        background: white;
        border-radius: 12px;
        border: 1px solid #E4E7EC;
        padding: 1.5rem !important;
        box-shadow: 0 2px 8px rgba(16,24,40,0.07);
        margin-top: 0.75rem;
        align-items: start !important;
    }

    /* ── Save-to-list panel ── */
    [data-testid="stVerticalBlock"]:has(.save-panel-anchor) {
        background: #FAFBFF;
        border: 1px solid #E0E7FF;
        border-left: 3px solid #2D6BE4;
        border-radius: 0 8px 8px 0;
        padding: 0.75rem 1rem !important;
        margin-bottom: 0.5rem;
    }

    /* ── Progress bars ── */
    .stProgress > div > div { background: #2D6BE4 !important; }

    /* ── Alerts ── */
    [data-testid="stAlert"] { border-radius: 8px !important; }

    /* ── Toggle ── */
    .stToggle label p { font-size: 0.85rem !important; color: #344054 !important; }

    /* ── Dividers ── */
    hr { border-color: #E4E7EC !important; margin: 0.875rem 0 !important; }

    /* ── Multiselect tags ── */
    .stMultiSelect [data-baseweb="tag"] {
        background: #DBEAFE !important;
        color: #1D4ED8 !important;
        border-radius: 4px !important;
    }

    /* ── st.html containers ── */
    [data-testid="stHtml"] { line-height: 1; }

    /* ── Textarea ── */
    [data-testid="stMain"] textarea {
        background: white !important;
        border: 1px solid #E4E7EC !important;
        color: #344054 !important;
        border-radius: 6px !important;
        font-size: 0.8rem !important;
        resize: vertical !important;
    }
    [data-testid="stMain"] textarea:focus { border-color: #93C5FD !important; }
    [data-testid="stMain"] textarea::placeholder { color: #C8D3E0 !important; }
    </style>
    """, unsafe_allow_html=True)


def get_store():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return PropertyStore(DB_PATH)


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


def _run_collection_thread(store_path, search_id, cancel_event, progress_queue):
    from src.buyer.collector import run_collection
    from src.buyer.property_store import PropertyStore
    from src.scraper_manager import ScraperManager

    store = PropertyStore(store_path)
    manager = ScraperManager()
    try:
        run_id = run_collection(
            store,
            search_id,
            manager,
            on_progress=progress_queue.put,
            should_cancel=cancel_event.is_set,
        )
        progress_queue.put({"status": store.get_run(run_id)["status"]})
    except Exception as exc:
        progress_queue.put({"status": "error", "error": str(exc)})
    finally:
        store.close()


def _drain_progress(collection):
    while True:
        try:
            collection["progress"].update(collection["progress_queue"].get_nowait())
        except queue.Empty:
            return


@st.fragment(run_every="2s")
def _render_collection_controls(store_path, search_id):
    collection = st.session_state.get("collection")
    if collection and collection["thread"].is_alive():
        _drain_progress(collection)
        progress = collection["progress"]
        if collection["cancel_event"].is_set():
            st.warning("Cancelling…")
        else:
            checked = progress.get("checked", 0)
            saved = progress.get("saved", 0)
            st.html(
                f'<p style="color:#93C5FD;font-size:0.8rem;margin:0">Checked {checked} · Saved {saved}</p>'
            )
            if st.button("Stop", key="cancel_btn"):
                collection["cancel_event"].set()
        return

    if collection:
        _drain_progress(collection)
        status = collection["progress"].get("status")
        if status == "cancelled":
            st.warning("Collection stopped.")
        elif status == "error":
            st.error(collection["progress"].get("error", "Unknown error"))
        else:
            st.success("Done.")
        st.session_state.pop("collection")

    if st.button("Run collection", type="primary", key="run_btn"):
        cancel_event = threading.Event()
        progress_queue = queue.Queue()
        thread = threading.Thread(
            target=_run_collection_thread,
            args=(store_path, search_id, cancel_event, progress_queue),
            daemon=True,
        )
        st.session_state.collection = {
            "thread": thread,
            "cancel_event": cancel_event,
            "progress_queue": progress_queue,
            "progress": {"checked": 0, "saved": 0, "status": "running"},
        }
        thread.start()
        st.rerun(scope="fragment")


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


def _listing_image_urls(listing):
    all_details = listing.get("all_property_details") or {}
    values = [
        listing.get("image_url_1"),
        listing.get("image_url_2"),
        all_details.get("Image 1 URL"),
        all_details.get("Image 2 URL"),
    ]
    images = listing.get("images")
    if isinstance(images, (list, tuple)):
        values.extend(images)
    urls = []
    for value in values:
        if isinstance(value, str) and value.strip().startswith(("http://", "https://")):
            url = value.strip()
            if url not in urls:
                urls.append(url)
    return urls


def _epc_pill(epc):
    color = _EPC_COLORS.get(epc, "#6B7280")
    label = epc or "?"
    return (
        f'<span style="display:inline-block;background:{color};color:white;'
        f'border-radius:20px;font-size:0.68rem;font-weight:700;'
        f'padding:2px 9px;line-height:1.6;letter-spacing:0.01em">EPC {label}</span>'
    )


def _score_html(score):
    if score is None:
        return '<span style="font-size:1.3rem;font-weight:700;color:#D1D5DB">—</span>'
    color = _SCORE_COLOR["high"] if score >= 60 else _SCORE_COLOR["mid"] if score >= 40 else _SCORE_COLOR["low"]
    return (
        f'<span style="font-size:1.5rem;font-weight:700;color:{color};line-height:1">{score:.0f}</span>'
        f'<span style="font-size:0.65rem;color:#9CA3AF;vertical-align:super;margin-left:1px">/100</span>'
    )


def _score_badge_html(score):
    if score is None:
        return '<span style="display:inline-block;background:#F2F4F7;color:#98A2B3;font-size:0.68rem;font-weight:600;padding:2px 9px;border-radius:20px;line-height:1.6">—</span>'
    bg, color = (
        ("#ECFDF5", "#027A48") if score >= 60
        else ("#FFFAEB", "#B54708") if score >= 40
        else ("#FFF1F3", "#C01048")
    )
    return f'<span style="display:inline-block;background:{bg};color:{color};font-size:0.68rem;font-weight:700;padding:2px 9px;border-radius:20px;line-height:1.6">{score:.0f}</span>'


def _apply_table_filters(listings, filters):
    result = listings
    if filters["sources"]:
        result = [l for l in result if l.get("source") in filters["sources"]]
    if filters["postcodes"]:
        result = [l for l in result if str(l.get("postcode", "")) in filters["postcodes"]]
    if filters["epc_labels"]:
        result = [l for l in result if l.get("epc_score") in filters["epc_labels"]]
    if filters["min_bedrooms"] is not None:
        result = [l for l in result if (l.get("bedrooms") or 0) >= filters["min_bedrooms"]]
    if filters["min_surface"] is not None:
        result = [l for l in result if (l.get("surface_area") or 0) >= filters["min_surface"]]
    if filters["max_surface"] is not None:
        result = [l for l in result if (l.get("surface_area") or 0) <= filters["max_surface"]]
    if filters["terrace_only"]:
        result = [l for l in result if l.get("outdoor_terrace") or l.get("outdoor_surface")]
    return result


def _card_image_html(listing):
    urls = _listing_image_urls(listing)
    if not urls:
        return (
            '<div style="width:100%;height:96px;background:#F2F4F7;border-radius:8px;'
            'display:flex;align-items:center;justify-content:center;'
            'color:#D0D5DD;font-size:1.5rem">🏠</div>'
        )
    return (
        f'<img src="{urls[0]}" style="width:100%;height:96px;object-fit:cover;'
        f'border-radius:8px;display:block" />'
    )



@st.fragment(run_every="2s")
def _render_listings(config):
    store = get_store()
    try:
        listings = store.latest_listings("sale")
        scored = _score_and_filter(listings, config)

        passing = [l for l in scored if l["_score"] is not None]
        excluded = [l for l in scored if l["_score"] is None]

        m1, m2, m3 = st.columns(3)
        m1.metric("In store", len(listings))
        m2.metric("Pass filters", len(passing))
        m3.metric("Excluded", len(excluded))

        if not listings:
            st.info("No listings yet. Run a collection from the sidebar.")
            return

        show_excluded = st.toggle("Show excluded", value=False)
        display_list = passing + (excluded if show_excluded else [])

        all_sources = sorted({l.get("source", "") for l in display_list if l.get("source")})
        all_postcodes = sorted({str(l.get("postcode", "")) for l in display_list if l.get("postcode")})
        all_epc = ["A++", "A+", "A", "B", "C", "D", "E", "F", "G"]

        with st.expander("Filters", expanded=False):
            fc1, fc2, fc3 = st.columns(3)
            sel_sources = fc1.multiselect("Portal", all_sources, key="filter_sources")
            sel_postcodes = fc2.multiselect("Postcode", all_postcodes, key="filter_postcodes")
            sel_epc = fc3.multiselect("EPC", all_epc, key="filter_epc")
            fd1, fd2, fd3, fd4 = st.columns(4)
            min_beds = fd1.number_input("Min beds", 0, 10, 0, 1, key="filter_min_beds")
            min_sqm = fd2.number_input("Min m²", 0, 1000, 0, 5, key="filter_min_sqm")
            max_sqm = fd3.number_input("Max m²", 0, 1000, 0, 5, key="filter_max_sqm")
            terrace_only = fd4.checkbox("Terrace / garden", key="filter_terrace")

        filters = {
            "sources": set(sel_sources),
            "postcodes": set(sel_postcodes),
            "epc_labels": set(sel_epc),
            "min_bedrooms": min_beds if min_beds > 0 else None,
            "min_surface": min_sqm if min_sqm > 0 else None,
            "max_surface": max_sqm if max_sqm > 0 else None,
            "terrace_only": terrace_only,
        }
        display_list = _apply_table_filters(display_list, filters)

        checked_urls = {
            key[len("delete_check_"):]: True
            for key, val in st.session_state.items()
            if key.startswith("delete_check_") and val
        }
        n_sel = len(checked_urls)
        n_shown = len(display_list)

        sel_label = f"<b style='color:#2D6BE4'>{n_sel} selected</b>" if n_sel else f"{n_shown} properties"
        st.html(
            f'<div style="display:flex;align-items:center;padding:0.35rem 0 0.5rem;'
            f'border-bottom:1px solid #E4E7EC;margin-bottom:0.6rem">'
            f'<span style="font-size:0.78rem;color:#667085;font-family:inherit">{sel_label}</span>'
            f'</div>'
        )

        bc1, bc2, _ = st.columns([1.1, 1.4, 5.5])
        with bc1:
            if n_sel:
                if st.button("Deselect all"):
                    for l in display_list:
                        st.session_state.pop(f"delete_check_{l.get('url', '')}", None)
                    st.rerun(scope="fragment")
            else:
                if st.button("Select all"):
                    for l in display_list:
                        st.session_state[f"delete_check_{l.get('url', '')}"] = True
                    st.rerun(scope="fragment")
        with bc2:
            if n_sel:
                if st.button(f"Delete {n_sel} selected", type="secondary"):
                    url_map = {l.get("url"): l for l in display_list}
                    for u in list(checked_urls):
                        lst = url_map.get(u)
                        if lst:
                            try:
                                store.delete_listing(lst["source"], str(lst["source_listing_id"]))
                            except Exception:
                                pass
                        st.session_state.pop(f"delete_check_{u}", None)
                    st.rerun(scope="fragment")
            elif n_shown:
                if st.button("Delete all", type="secondary"):
                    for lst in display_list:
                        try:
                            store.delete_listing(lst["source"], str(lst["source_listing_id"]))
                        except Exception:
                            pass
                    st.rerun(scope="fragment")

        all_lists = store.get_lists(USER_ID)
        all_notes = store.get_all_notes(USER_ID)

        selected_url = st.session_state.get("selected_url")
        saving_url = st.session_state.get("saving_url")

        for i, listing in enumerate(display_list):
            url = listing.get("url", "")
            src = listing.get("source", "")
            lid = str(listing.get("source_listing_id", ""))
            is_selected = selected_url == url
            is_saving = saving_url == url
            score = listing.get("_score")

            prop_type = (listing.get("property_type") or "").title()
            postcode = listing.get("postcode") or "—"
            surface = listing.get("surface_area")
            bedrooms = listing.get("bedrooms")
            epc = listing.get("epc_score") or None
            source = (src or "").lower()
            in_list_ids = store.get_property_list_ids(USER_ID, src, lid) if all_lists else set()
            has_note = bool(all_notes.get((src, lid), ""))

            specs = " · ".join(filter(None, [
                f"{int(bedrooms)} bd" if bedrooms else None,
                f"{int(surface)} m²" if surface else None,
                postcode,
            ]))

            _pill = 'display:inline-block;border-radius:20px;font-size:0.68rem;padding:2px 9px;line-height:1.6'
            source_badge = f'<span style="{_pill};background:#F2F4F7;color:#667085">{source}</span>'
            excluded_tag = (
                f'<span style="{_pill};background:#FFF1F3;color:#C01048">excluded</span>'
                if score is None else ""
            )
            saved_tag = (
                f'<span style="{_pill};background:#EEF2FF;color:#4338CA">saved</span>'
                if in_list_ids else ""
            )
            note_tag = (
                f'<span style="{_pill};background:#F0FDF4;color:#027A48">note</span>'
                if has_note else ""
            )

            desc_display = listing.get("description_english") or ""
            desc_snippet = (desc_display[:260] + "…") if len(desc_display) > 260 else desc_display
            score_badge = _score_badge_html(score)

            with st.container():
                c_sel, c_img, c_data, c_desc, c_btns = st.columns([0.28, 1.45, 3.2, 2.75, 0.85])

                c_sel.checkbox("Select", key=f"delete_check_{url}", label_visibility="collapsed")

                with c_img:
                    st.html(_card_image_html(listing))

                with c_data:
                    st.html(
                        f'<span class="listing-row-anchor"></span>'
                        f'<div style="padding:0.25rem 0 0.15rem;font-family:inherit">'
                        f'<div style="display:flex;align-items:center;gap:0.45rem;flex-wrap:wrap;margin-bottom:0.22rem">'
                        f'<span style="font-size:1.1rem;font-weight:600;color:#101828;line-height:1.2">{_fmt_price(listing.get("price"))}</span>'
                        f'<span style="font-size:0.8rem;font-weight:400;color:#667085">{prop_type}</span>'
                        f'<span style="margin-left:auto">{score_badge}</span>'
                        f'</div>'
                        f'<div style="font-size:0.775rem;color:#667085;margin-bottom:0.28rem">{specs}</div>'
                        f'<div style="display:flex;gap:5px;flex-wrap:wrap;align-items:center">'
                        f'{_epc_pill(epc) if epc else ""}'
                        f'{source_badge}'
                        f'{excluded_tag}'
                        f'{saved_tag}'
                        f'{note_tag}'
                        f'</div>'
                        f'</div>'
                    )

                with c_desc:
                    if desc_snippet:
                        st.html(
                            f'<p style="font-size:0.75rem;color:#667085;line-height:1.55;'
                            f'margin:0.2rem 0 0;font-family:inherit;display:-webkit-box;'
                            f'-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden">'
                            f'{desc_snippet}'
                            f'</p>'
                        )

                with c_btns:
                    view_label = "Close" if is_selected else "View"
                    if st.button(view_label, key=f"detail_{i}", use_container_width=True):
                        st.session_state.selected_url = None if is_selected else url
                        st.rerun(scope="fragment")
                    list_label = "✕ Lists" if is_saving else "📋 Lists"
                    if st.button(list_label, key=f"save_{i}", use_container_width=True):
                        st.session_state.saving_url = None if is_saving else url
                        st.rerun(scope="fragment")

            if is_saving:
                _render_save_to_list(store, all_lists, src, lid, all_notes.get((src, lid), ""))

            if is_selected:
                _render_detail(listing)
    finally:
        store.close()


def _render_save_to_list(store, all_lists, src, lid, existing_note=""):
    CREATE_OPT = "＋ New list…"
    in_list_ids = store.get_property_list_ids(USER_ID, src, lid)
    in_lists = [lst for lst in all_lists if lst["id"] in in_list_ids]
    available = [lst for lst in all_lists if lst["id"] not in in_list_ids]

    with st.container():
        st.html('<span class="save-panel-anchor" style="display:none"></span>')

        pl, pr = st.columns([5, 2])
        with pl:
            opts = [lst["name"] for lst in available] + [CREATE_OPT]
            picked = st.selectbox(
                "Add to list",
                opts,
                label_visibility="collapsed",
                key=f"list_pick_{src}_{lid}",
            )

        if picked == CREATE_OPT:
            cn, cc = st.columns([4, 1])
            with cn:
                new_name = st.text_input(
                    "Name",
                    label_visibility="collapsed",
                    key=f"list_new_{src}_{lid}",
                    placeholder="List name…",
                )
            with cc:
                if st.button("Create", key=f"list_add_{src}_{lid}", type="primary"):
                    if new_name.strip():
                        list_id = store.create_list(USER_ID, new_name.strip())
                        store.add_to_list(USER_ID, list_id, src, lid)
                        st.session_state.saving_url = None
                        st.rerun(scope="fragment")
        else:
            with pr:
                if st.button("Add to list", key=f"list_add_{src}_{lid}", type="primary"):
                    for lst in all_lists:
                        if lst["name"] == picked:
                            store.add_to_list(USER_ID, lst["id"], src, lid)
                            st.session_state.saving_url = None
                    st.rerun(scope="fragment")

        if in_lists:
            badges = " ".join(
                f'<span style="display:inline-block;background:#EEF2FF;color:#4338CA;'
                f'border-radius:20px;font-size:0.7rem;font-weight:500;padding:2px 10px">{lst["name"]}</span>'
                for lst in in_lists
            )
            st.html(f'<div style="margin:0.3rem 0 0.2rem;font-family:inherit">{badges}</div>')
            rr, rb = st.columns([4, 1])
            with rr:
                rem = st.selectbox(
                    "Remove",
                    [""] + [lst["name"] for lst in in_lists],
                    label_visibility="collapsed",
                    key=f"list_rem_{src}_{lid}",
                    placeholder="Remove from list…",
                )
            with rb:
                if st.button("Remove", key=f"list_rem_btn_{src}_{lid}"):
                    if rem:
                        for lst in all_lists:
                            if lst["name"] == rem:
                                store.remove_from_list(USER_ID, lst["id"], src, lid)
                        st.rerun(scope="fragment")

        st.html('<div style="border-top:1px solid #E4E7EC;margin:0.5rem 0 0.4rem"></div>')

        note_key = f"note_panel_{src}_{lid}"
        if note_key not in st.session_state:
            st.session_state[note_key] = existing_note
        nc, nb = st.columns([5, 1])
        with nc:
            st.text_area("Note", key=note_key, height=72, label_visibility="collapsed", placeholder="Notes about this property…")
        with nb:
            st.html('<div style="height:0.4rem"></div>')
            if st.button("Save", key=f"note_save_{src}_{lid}", type="primary"):
                store.save_note(USER_ID, src, lid, st.session_state[note_key])
                st.rerun(scope="fragment")


def _render_detail(listing):
    score = listing.get("_score")
    score_color = (
        _SCORE_COLOR["high"] if score and score >= 60
        else _SCORE_COLOR["mid"] if score and score >= 40
        else _SCORE_COLOR["low"] if score
        else _SCORE_COLOR["none"]
    )
    urls = _listing_image_urls(listing)

    st.divider()

    left, right = st.columns([3, 2])

    with left:
        st.html('<span class="detail-panel-anchor" style="display:none"></span>')

        name = listing.get("name") or listing.get("address") or listing.get("street") or ""
        if name:
            st.html(f'<p style="font-size:1rem;font-weight:600;color:#111827;margin:0 0 0.6rem;font-family:inherit">{name}</p>')

        m1, m2, m3, m4 = st.columns(4)
        price = listing.get("price")
        price_label = f"€{int(price)//1000}K" if price else "—"
        m1.metric("Price", price_label)
        m2.metric("Surface", f"{listing.get('surface_area', '?')} m²")
        m3.metric("Beds", listing.get("bedrooms") or "?")
        m4.metric("EPC", listing.get("epc_score") or "?")

        if score is not None:
            st.html(f'<p style="font-size:0.8rem;color:{score_color};font-weight:600;margin:0.75rem 0 0.4rem;font-family:inherit">Score {score:.0f} / 100</p>')
            comp_labels = {
                "price": ("Price headroom", 30),
                "surface_area": ("Surface", 25),
                "bedrooms": ("Bedrooms", 15),
                "epc": ("EPC", 20),
                "completeness": ("Data completeness", 10),
            }
            components = listing.get("_components", {})
            for key, (label, max_val) in comp_labels.items():
                val = components.get(key, 0)
                pct = val / max_val if max_val else 0
                st.html(
                    f'<div style="display:flex;justify-content:space-between;font-size:0.75rem;color:#6B7280;margin-bottom:2px;font-family:inherit">'
                    f'<span>{label}</span><span style="font-weight:600;color:#374151">{val:.0f} / {max_val}</span>'
                    f'</div>'
                )
                st.progress(pct)
        else:
            exclusions = listing.get("_exclusions", [])
            st.warning(f"Excluded: {', '.join(exclusions) or 'fails hard filters'}")

        st.link_button("Open on portal ↗", listing.get("url", "#"))

    with right:
        if urls:
            index_key = "detail_img_idx"
            idx = st.session_state.get(index_key, 0) % len(urls)
            st.html(
                f'<img src="{urls[idx]}" style="width:100%;border-radius:8px;object-fit:cover;max-height:220px;display:block" />'
            )
            if len(urls) > 1:
                pa, pb = st.columns(2)
                if pa.button("‹ Prev", key="detail_prev"):
                    st.session_state[index_key] = (idx - 1) % len(urls)
                    st.rerun(scope="fragment")
                if pb.button("Next ›", key="detail_next"):
                    st.session_state[index_key] = (idx + 1) % len(urls)
                    st.rerun(scope="fragment")
                st.caption(f"{idx + 1} / {len(urls)}")

        details = [
            ("Postcode", listing.get("postcode")),
            ("Type", (listing.get("property_type") or "").title()),
            ("Portal", listing.get("source")),
            ("Built", listing.get("construction_year")),
            ("Terrace", listing.get("outdoor_surface") or (listing.get("outdoor_terrace") and "Yes")),
        ]
        rows_html = "".join(
            f'<tr>'
            f'<td style="color:#9CA3AF;font-size:0.75rem;padding:3px 0;padding-right:1rem;white-space:nowrap">{k}</td>'
            f'<td style="color:#374151;font-size:0.78rem;font-weight:500;padding:3px 0">{v}</td>'
            f'</tr>'
            for k, v in details if v
        )
        if rows_html:
            st.html(f'<table style="border-collapse:collapse;width:100%;font-family:inherit">{rows_html}</table>')

        display_desc = listing.get("description_english") or ""

        if display_desc:
            st.html(
                f'<p style="font-size:0.75rem;color:#6B7280;line-height:1.55;margin:0.75rem 0 0;font-family:inherit">'
                f'{display_desc[:600]}{"…" if len(display_desc) > 600 else ""}'
                f'</p>'
            )



@st.fragment(run_every="2s")
def _render_history(search_id):
    store = get_store()
    try:
        runs = _last_runs(store, search_id)
        if not runs:
            st.info("No runs yet.")
            return

        for run in runs:
            started = run["started_at"][:19].replace("T", " ") if run["started_at"] else "?"
            completed = run["completed_at"][:19].replace("T", " ") if run["completed_at"] else "in progress"
            label_color = {
                "ok": "#059669", "partial": "#D97706",
                "cancelled": "#6B7280", "running": "#2D6BE4",
            }.get(run["status"], "#374151")
            icon = {"ok": "✓", "partial": "~", "cancelled": "⏹", "running": "↻"}.get(run["status"], "?")

            with st.expander(f"Run #{run['id']} — {started}", expanded=False):
                st.html(
                    f'<span style="color:{label_color};font-weight:600;font-size:0.8rem;font-family:inherit">{icon}</span> '
                    f'<span style="font-weight:600;font-family:inherit">Run #{run["id"]}</span>'
                    f'<span style="color:#9CA3AF;font-size:0.8rem;margin-left:0.5rem;font-family:inherit">'
                    f'{started} → {completed}</span>'
                )

                sources_raw = run.get("sources") or ""
                if sources_raw:
                    for part in sources_raw.split("|"):
                        bits = part.split(":")
                        if len(bits) == 3:
                            src, src_status, count = bits
                            dot_color = "#059669" if src_status == "ok" else "#DC2626"
                            st.html(
                                f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;'
                                f'background:{dot_color};margin-right:6px;vertical-align:middle"></span>'
                                f'<span style="font-size:0.8rem;color:#374151;font-family:inherit"><b>{src}</b> — {count} saved</span>'
                            )

                listings = store.listings_for_run(run["id"])
                if not listings:
                    st.caption("Nothing saved in this run.")
                    continue

                st.html(
                    '<div style="display:grid;grid-template-columns:2.5fr 1.2fr 1fr 0.8fr 0.8fr 0.8fr 0.8fr 0.9fr;'
                    'font-size:0.68rem;font-weight:600;color:#9CA3AF;letter-spacing:0.05em;text-transform:uppercase;'
                    'padding:0.5rem 0 0.4rem;border-bottom:1px solid #F3F4F6;margin-bottom:0.25rem;font-family:inherit">'
                    '<div>Address</div><div>Price</div><div>Type</div><div>Post</div>'
                    '<div>m²</div><div>Beds</div><div>EPC</div><div>Portal</div>'
                    '</div>'
                )

                for listing in listings:
                    url = listing.get("url", "")
                    name = listing.get("name") or listing.get("address") or listing.get("street") or url
                    short_name = (name[:38] + "…") if len(name) > 38 else name
                    epc = listing.get("epc_score") or ""
                    epc_color = _EPC_COLORS.get(epc, "#9CA3AF")

                    st.html(
                        f'<div style="display:grid;grid-template-columns:2.5fr 1.2fr 1fr 0.8fr 0.8fr 0.8fr 0.8fr 0.9fr;'
                        f'border-bottom:1px solid #F9FAFB;padding:0.35rem 0;align-items:center;font-family:inherit">'
                        f'<div><a href="{url}" target="_blank" '
                        f'style="color:#2D6BE4;font-size:0.8rem;text-decoration:none">{short_name}</a></div>'
                        f'<div style="font-size:0.8rem;font-weight:600;color:#111827">{_fmt_price(listing.get("price"))}</div>'
                        f'<div style="font-size:0.78rem;color:#374151">{(listing.get("property_type") or "").title()}</div>'
                        f'<div style="font-size:0.78rem;color:#6B7280">{listing.get("postcode") or "—"}</div>'
                        f'<div style="font-size:0.78rem;color:#6B7280">{listing.get("surface_area") or "?"}</div>'
                        f'<div style="font-size:0.78rem;color:#6B7280">{listing.get("bedrooms") or "?"}</div>'
                        f'<div style="font-size:0.72rem;font-weight:700;color:{epc_color}">{epc or "—"}</div>'
                        f'<div style="font-size:0.72rem;color:#9CA3AF">{listing.get("source") or "—"}</div>'
                        f'</div>'
                    )
    finally:
        store.close()


def _render_search_config_editor(search_id, config):
    from src.buyer.search_config import AVAILABLE_PORTALS, normalize_search_config

    ALL_EPC = ["A++", "A+", "A", "B", "C", "D", "E", "F", "G"]

    with st.form("search_config_form", border=False):
        postcodes_raw = st.text_input("Postcodes", value=", ".join(config["postcodes"]), placeholder="2000, 2018, 2060")
        max_price = st.number_input("Max price (€)", 0, 5_000_000, int(config["max_price"] or 0), 5000)
        min_surface = st.number_input("Min surface (m²)", 0, 1000, int(config["min_surface_area"] or 0), 5)
        min_bedrooms = st.number_input("Min bedrooms", 0, 10, int(config["min_bedrooms"] or 0), 1)
        epc_labels = st.multiselect("EPC labels", ALL_EPC, default=config["epc_labels"])
        portals = st.multiselect("Portals", list(AVAILABLE_PORTALS), default=config["portals"])
        max_pages = st.number_input("Pages per portal", 1, 50, int(config["max_pages"] or 5), 1)

        if st.form_submit_button("Save", type="primary", use_container_width=True):
            postcodes = [p.strip() for p in postcodes_raw.split(",") if p.strip()]
            new_config = {
                **config,
                "postcodes": postcodes,
                "max_price": max_price or None,
                "min_surface_area": min_surface or None,
                "min_bedrooms": min_bedrooms or None,
                "epc_labels": epc_labels,
                "portals": portals,
                "max_pages": max_pages,
            }
            try:
                normalize_search_config(new_config)
                s = get_store()
                try:
                    s.save_search(USER_ID, SEARCH_NAME, "home", new_config)
                finally:
                    s.close()
                st.success("Saved.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


@st.fragment(run_every="10s")
def _render_lists():
    store = get_store()
    try:
        all_lists = store.get_lists(USER_ID)
        all_notes = store.get_all_notes(USER_ID)

        if not all_lists:
            st.info("No lists yet. Use the 📋 button on any listing to save it.")
            return

        nl, nn = st.columns([3, 1])
        with nl:
            new_list_name = st.text_input("New list name", label_visibility="collapsed", placeholder="Create new list…", key="new_list_name_tab")
        with nn:
            if st.button("Create", type="primary", key="create_list_btn"):
                if new_list_name.strip():
                    store.create_list(USER_ID, new_list_name.strip())
                    st.rerun(scope="fragment")

        st.html('<div style="margin-top:0.5rem"></div>')

        for lst in all_lists:
            list_id = lst["id"]
            count = lst["item_count"]
            expand_key = f"list_expanded_{list_id}"
            header_label = f"📋 {lst['name']} · {count} {'property' if count == 1 else 'properties'}"

            with st.expander(header_label, expanded=st.session_state.get(expand_key, False)):
                items = store.get_list_items(USER_ID, list_id)
                if not items:
                    st.caption("Empty list.")
                else:
                    for item in items:
                        item_src = item.get("source", "")
                        item_lid = str(item.get("source_listing_id", ""))
                        note = all_notes.get((item_src, item_lid), "")
                        url = item.get("url", "")
                        price = item.get("price")
                        prop_type = (item.get("property_type") or "").title()
                        postcode = item.get("postcode") or "—"
                        surface = item.get("surface_area")
                        bedrooms = item.get("bedrooms")
                        epc = item.get("epc_score") or None
                        specs = " · ".join(filter(None, [
                            f"{int(bedrooms)} bd" if bedrooms else None,
                            f"{int(surface)} m²" if surface else None,
                            postcode,
                        ]))

                        with st.container():
                            ci, cd, cr = st.columns([1.2, 4.5, 1])
                            with ci:
                                st.html(_card_image_html(item))
                            with cd:
                                st.html(
                                    f'<div style="font-size:1rem;font-weight:600;color:#111827">{_fmt_price(price)}'
                                    f'<span style="font-size:0.78rem;font-weight:400;color:#6B7280;margin-left:0.4rem">{prop_type}</span></div>'
                                    f'<div style="font-size:0.75rem;color:#6B7280;margin-top:2px">{specs}</div>'
                                    f'<div style="margin-top:4px">{_epc_pill(epc) if epc else ""}</div>'
                                )
                                if note:
                                    st.html(
                                        f'<p style="font-size:0.72rem;color:#374151;background:#F9FAFB;border-left:3px solid #C7D2FE;'
                                        f'padding:4px 8px;border-radius:0 4px 4px 0;margin:6px 0 0;font-family:inherit">{note}</p>'
                                    )
                            with cr:
                                st.link_button("Open ↗", url)
                                if st.button("Remove", key=f"rm_{list_id}_{item_src}_{item_lid}"):
                                    store.remove_from_list(USER_ID, list_id, item_src, item_lid)
                                    st.rerun(scope="fragment")

                st.html('<div style="height:0.5rem"></div>')
                if st.button(f"Delete list '{lst['name']}'", key=f"delete_list_{list_id}"):
                    store.delete_list(USER_ID, list_id)
                    st.rerun(scope="fragment")
    finally:
        store.close()


def main():
    _inject_css()

    store = get_store()
    try:
        search_id = store.save_search(USER_ID, SEARCH_NAME, "home", DEFAULT_HOME_SEARCH)
        config = store.get_search(search_id)["config"]
    finally:
        store.close()

    with st.sidebar:
        st.html(
            '<p style="color:#E0E7FF;font-size:1rem;font-weight:600;margin:0 0 0.1rem;letter-spacing:-0.01em;font-family:inherit">Immowbot</p>'
            '<p style="color:#6366F1;font-size:0.72rem;margin:0 0 1.25rem;font-family:inherit">Antwerp buyer</p>'
        )
        st.header("Search")
        _render_search_config_editor(search_id, config)
        st.divider()
        st.header("Collection")
        _render_collection_controls(os.path.abspath(DB_PATH), search_id)
        st.divider()
        st.caption(f"buyer.db · {DB_PATH.split(os.sep)[-2]}")

    st.title("Listings")

    tab_listings, tab_history, tab_lists = st.tabs(["Active", "Run history", "Lists"])

    with tab_listings:
        _render_listings(config)

    with tab_history:
        _render_history(search_id)

    with tab_lists:
        _render_lists()


if __name__ == "__main__":
    main()
