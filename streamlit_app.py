import streamlit as st
import os
import json
from datetime import datetime, timedelta
import streamlit.components.v1 as components
from PIL import Image
from src.orchestrator import PulseOrchestrator
from src.email_service import EmailService
from src.db_init import ensure_initialized
import concurrent.futures
import time

# --- App Config ---
st.set_page_config(page_title="Weekly App Review Pulse", layout="wide")

# --- Brand Theme CSS ---
st.markdown("""
<style>
    /* ===== Brand Colors =====
       Brand Blue:            #5367F5
       Brand Green (Logo):    #08F6B6
       Brand Green (Primary): #00D09C
       Brand Accent Blue A:   #B1D0FB
       Brand Accent Blue B:   #E5F4FD
    */

    /* Primary buttons */
    .stButton > button[kind="primary"],
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #00D09C !important;
        border-color: #00D09C !important;
        color: #FFFFFF !important;
    }
    .stButton > button[kind="primary"]:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #08F6B6 !important;
        border-color: #08F6B6 !important;
    }

    /* Secondary / default buttons */
    .stButton > button:not([kind="primary"]) {
        border-color: #00D09C !important;
        color: #0B0B21 !important;
    }
    .stButton > button:not([kind="primary"]):hover {
        background-color: #EBFCF4 !important;
        border-color: #00D09C !important;
    }

    /* Title styling */
    h1 {
        color: #0B0B21 !important;
    }

    /* Sidebar header */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2 {
        color: #5367F5 !important;
    }

    /* Dividers */
    hr {
        border-color: #B1D0FB !important;
    }

    /* Links and accents */
    a {
        color: #5367F5 !important;
    }

    /* Success alerts */
    div[data-testid="stAlert"][data-baseweb="notification"]:has([data-testid="stNotificationContentSuccess"]) {
        background-color: #EBFCF4 !important;
        border-left-color: #00D09C !important;
    }

    /* Error alerts */
    div[data-testid="stAlert"][data-baseweb="notification"]:has([data-testid="stNotificationContentError"]) {
        border-left-color: #5367F5 !important;
    }

    /* Metric value */
    [data-testid="stMetricValue"] {
        color: #00D09C !important;
    }

    /* Bordered containers */
    [data-testid="stVerticalBlock"] > div[data-testid="stExpander"],
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #B1D0FB !important;
    }

    /* Spinner */
    .stSpinner > div {
        border-top-color: #00D09C !important;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_orchestrator():
    return PulseOrchestrator()

@st.cache_resource
def get_executor():
    return concurrent.futures.ThreadPoolExecutor(max_workers=1)


# --- Database Initialization (runs once per container; idempotent on reruns) ---
ensure_initialized()

orchestrator = get_orchestrator()
executor = get_executor()


# --- Query Param Handling (Deep Linking) ---
# Check if a specific report is requested via URL (e.g. /?run_id=2023-W23)
query_params = st.query_params
if "run_id" in query_params:
    target_run_id = query_params["run_id"]
    # Only load if not already loaded or different
    if st.session_state.get('latest_result', {}).get('run_id') != target_run_id:
        processed_dir = "data/processed"
        analysis_path = os.path.join(processed_dir, f"analysis_{target_run_id}.json")
        email_path = os.path.join(processed_dir, f"pulse_email_{target_run_id}.html")
        
        if os.path.exists(email_path):
            t_count = 0
            # Try to load stats from DB first
            run_log = orchestrator.data_manager.get_run_log(target_run_id)
            reviews_count = run_log.get('reviews_processed', 'N/A')
            themes_count = run_log.get('themes_identified', 'N/A')

            # Fallback to file reading if DB miss
            if not run_log:
                if os.path.exists(analysis_path):
                    try:
                        with open(analysis_path, 'r') as af:
                            t_count = len(json.load(af))
                            themes_count = t_count
                    except: pass
            
            st.session_state['latest_result'] = {
                "status": "success",
                "run_id": target_run_id,
                "reviews_count": reviews_count, 
                "themes_count": themes_count,
                "artifacts": {
                    "email_html": email_path
                }
            }

# --- Page Header ---
st.title("Weekly App Review Pulse")
st.markdown("Automated sentiment analysis and executive reporting for app store reviews.")

# --- Async Pipeline Status Check (placed AFTER header to avoid displacing title) ---
if 'pipeline_future' in st.session_state:
    future = st.session_state['pipeline_future']
    if future.done():
        # Clear future FIRST — prevents re-entry on subsequent reruns caused by polling
        del st.session_state['pipeline_future']
        try:
            result = future.result()
            if result["status"] == "success":
                # Idempotency guard: only toast once per run_id
                active_id  = st.session_state.get('pipeline_run_id')
                toasted_id = st.session_state.get('_toasted_run_id')
                if active_id and toasted_id != active_id:
                    st.toast(f"✅ Pipeline Succeeded! Reviews: {result['reviews_count']}", icon="✅")
                    st.session_state['_toasted_run_id'] = active_id
                st.session_state['latest_result'] = result
                st.session_state['pipeline_status'] = 'succeeded'
            else:
                err = result.get('error', 'Unknown error')
                st.toast(f"❌ Pipeline Failed: {err}", icon="❌")
                st.session_state['pipeline_status'] = 'failed'
                st.session_state['pipeline_error'] = err
        except Exception as e:
            st.session_state['pipeline_status'] = 'failed'
            st.session_state['pipeline_error'] = str(e)

# --- Sidebar ---
with st.sidebar:
    st.header("Pipeline Configuration")

    # Application Selection (fetched live from the applications table)
    from src.data_manager import DataManager
    _dm = DataManager()
    app_records = _dm.get_all_applications()
    app_names = [app["app_name"] for app in app_records]
    
    if not app_names:
        app_names = ["(no apps registered)"]
        selected_app = st.selectbox("Application", options=app_names, index=0)
    else:
        # ── Read selection written back by the JS dropdown ──────────────────
        if 'selected_app_dropdown' not in st.session_state:
            st.session_state.selected_app_dropdown = app_names[0]

        # If JS wrote a new selection via query param, absorb it & clear
        _qp_sel = st.query_params.get("_app_sel")
        if _qp_sel and _qp_sel in app_names:
            st.session_state.selected_app_dropdown = _qp_sel
        if "_app_sel" in st.query_params:
            del st.query_params["_app_sel"]

        selected_app = st.session_state.selected_app_dropdown

        # ── Build app data for the JS component ─────────────────────────────
        import json as _json
        _apps_js = _json.dumps(
            [{"name": a["app_name"], "logo": a.get("logo_url", "")} for a in app_records]
        )
        _sel_record = next((a for a in app_records if a["app_name"] == selected_app), app_records[0])
        _sel_logo   = _sel_record.get("logo_url", "")

        st.write("**Application**")

        # ── Full custom dropdown via components.html ─────────────────────────
        # The dropdown panel is appended to window.parent.document.body as
        # position:fixed so it is never clipped by the iframe boundary and
        # is completely free of Streamlit's CSS cascade.
        # Selection is communicated back by setting window.parent.location
        # query param "_app_sel" which Streamlit reads on next rerun.
        components.html(f"""
<!DOCTYPE html><html><head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: inherit; }}
  body {{ background: transparent; }}
  #trigger {{
    display: flex; align-items: center; gap: 8px;
    padding: 7px 12px;
    border: 1px solid #d0d5dd;
    border-radius: 6px;
    background: #fff;
    cursor: pointer;
    font-size: 14px;
    color: #1a1a2e;
    user-select: none;
    transition: border-color 0.15s;
    width: 100%;
  }}
  #trigger:hover {{ border-color: #5367F5; }}
  #trigger img {{ width: 22px; height: 22px; border-radius: 4px; object-fit: cover; flex-shrink: 0; }}
  #trigger-name {{ flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  #trigger-arrow {{ font-size: 10px; color: #666; flex-shrink: 0; }}
</style>
</head><body>
<div id="trigger" onclick="toggleMenu()">
  {'<img id="tri" src="' + _sel_logo + '" onerror="this.style.display=\'none\'" />' if _sel_logo else '<span style="font-size:18px">📱</span>'}
  <span id="trigger-name">{selected_app}</span>
  <span id="trigger-arrow">&#9660;</span>
</div>
<script>
const APPS   = {_apps_js};
const SEL    = {_json.dumps(selected_app)};
const PARENT = window.parent;
const PDOC   = PARENT.document;

// Inherit Streamlit's actual rendered font so trigger + panel match the UI
const _parentFont = window.getComputedStyle(PDOC.body).fontFamily
                    || '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
document.body.style.fontFamily = _parentFont;

let panel = null;
let open  = false;

function buildPanel() {{
  // Remove old panel if any
  const old = PDOC.getElementById('__app_dd_panel__');
  if (old) old.remove();

  panel = PDOC.createElement('div');
  panel.id = '__app_dd_panel__';

  const iframe = window.frameElement;
  const r = iframe.getBoundingClientRect();

  Object.assign(panel.style, {{
    position:     'fixed',
    top:          (r.bottom + 4) + 'px',
    left:         r.left + 'px',
    width:        r.width + 'px',
    zIndex:       '2147483647',
    background:   '#ffffff',
    border:       '1px solid #d0d5dd',
    borderRadius: '8px',
    boxShadow:    '0 4px 16px rgba(0,0,0,0.12)',
    padding:      '4px 0',
    overflow:     'hidden',
    animation:    'ddFadeIn 0.12s ease',
    fontFamily:   _parentFont,
  }});

  // Keyframe animation + item styles — inject once, includes parent font
  if (!PDOC.getElementById('__app_dd_kf__')) {{
    const kf = PDOC.createElement('style');
    kf.id = '__app_dd_kf__';
    kf.textContent = `
      @keyframes ddFadeIn {{ from {{ opacity:0; transform:translateY(-4px) }} to {{ opacity:1; transform:translateY(0) }} }}
      #__app_dd_panel__ div.dd-item {{
        display: flex; align-items: center; gap: 10px;
        padding: 8px 14px;
        cursor: pointer; font-size: 14px; color: #1a1a2e;
        font-family: ${{_parentFont}};
        transition: background 0.12s;
        white-space: nowrap;
      }}
      #__app_dd_panel__ div.dd-item:hover   {{ background: rgba(83,103,245,0.08); }}
      #__app_dd_panel__ div.dd-item.selected {{ background: rgba(83,103,245,0.13); font-weight: 600; }}
      #__app_dd_panel__ div.dd-item img {{
        width: 26px; height: 26px; border-radius: 5px; object-fit: cover; flex-shrink: 0;
      }}
    `;
    PDOC.head.appendChild(kf);
  }}

  APPS.forEach(app => {{
    const item = PDOC.createElement('div');
    item.className = 'dd-item' + (app.name === SEL ? ' selected' : '');
    if (app.logo) {{
      const img = PDOC.createElement('img');
      img.src = app.logo;
      img.onerror = () => {{ img.replaceWith(PDOC.createTextNode('📱')); }};
      item.appendChild(img);
    }} else {{
      item.appendChild(PDOC.createTextNode('📱'));
    }}
    const label = PDOC.createElement('span');
    label.textContent = app.name;
    item.appendChild(label);
    item.onclick = (e) => {{ e.stopPropagation(); selectApp(app.name); }};
    panel.appendChild(item);
  }});

  PDOC.body.appendChild(panel);
}}

function toggleMenu() {{
  if (open) {{ closeMenu(); }} else {{ openMenu(); }}
}}

function openMenu() {{
  buildPanel();
  open = true;
  document.getElementById('trigger-arrow').textContent = '\u25B2';
  // Close on outside click
  PDOC.addEventListener('click', outsideClick, true);
}}

function closeMenu() {{
  const p = PDOC.getElementById('__app_dd_panel__');
  if (p) p.remove();
  open = false;
  document.getElementById('trigger-arrow').textContent = '\u25BC';
  PDOC.removeEventListener('click', outsideClick, true);
}}

function outsideClick(e) {{
  const p = PDOC.getElementById('__app_dd_panel__');
  const trigger = window.frameElement; // the iframe in parent doc
  if (p && !p.contains(e.target) && !trigger.contains(e.target)) {{
    closeMenu();
  }}
}}

function selectApp(name) {{
  closeMenu();
  // Update trigger label immediately (optimistic UI)
  document.getElementById('trigger-name').textContent = name;
  const app = APPS.find(a => a.name === name);
  if (app) {{
    const tri = document.getElementById('tri');
    if (tri && app.logo) {{ tri.src = app.logo; tri.style.display = ''; }}
  }}
  // Communicate to Streamlit: set query param + pushState + popstate
  const url = new URL(PARENT.location.href);
  url.searchParams.set('_app_sel', name);
  PARENT.history.pushState({{}}, '', url.toString());
  PARENT.dispatchEvent(new PopStateEvent('popstate'));
  // Re-inject popstate after small delay to make sure Streamlit picks it up
  setTimeout(() => PARENT.dispatchEvent(new PopStateEvent('popstate')), 150);
}}
</script>
</body></html>
        """, height=46, scrolling=False)

    # Date Range Selection
    start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=7))
    end_date = st.date_input("End Date", value=datetime.now())

    if st.button("Generate Pulse Report", use_container_width=True):
        if selected_app == "(no apps registered)":
            st.error("No applications registered. Please add an app to the database first.")
        elif start_date > end_date:
            st.error("Error: Start date must be before end date.")
        else:
            # Prepare Custom Run ID for instant feedback
            timestamp = datetime.now().strftime('%H%M%S')
            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')
            custom_run_id = f"custom_{start_str}_{end_str}_{timestamp}"

            # Store selected app so the orchestrator can use it
            st.session_state['selected_app'] = selected_app

            # Async Submission
            dt_start = datetime.combine(start_date, datetime.min.time())
            dt_end = datetime.combine(end_date, datetime.max.time())
            
            future = executor.submit(
                orchestrator.run_pipeline,
                start_date=dt_start,
                end_date=dt_end,
                run_id=custom_run_id,
                app_name=selected_app
            )
            
            st.session_state['pipeline_future'] = future
            st.session_state['pipeline_run_id'] = custom_run_id
            st.session_state['pipeline_status'] = 'running'
            
            st.toast(f"Pipeline triggered: {custom_run_id}", icon="🚀")
            time.sleep(1) # Brief pause to let toast show
            st.rerun()

    # --- Maintenance Section ---
    st.divider()
    st.header("🛠️ Maintenance")

    if st.button("Purge All History", use_container_width=True):
        st.session_state.purge_val = ""
        st.session_state.show_maintenance_drawer = not st.session_state.get('show_maintenance_drawer', False)

    if st.session_state.get('show_maintenance_drawer'):
        with st.container(border=True):
            st.error("⚠️ Critical Action: Purging all data.")
            st.write("To confirm, please type **delete** below:")

            st.text_input("Confirm Delete", placeholder="delete", label_visibility="collapsed", key="purge_val")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("Confirm", type="primary", use_container_width=True):
                    if st.session_state.get("purge_val", "").strip().lower() == "delete":
                        with st.spinner("Purging all data..."):
                            try:
                                orchestrator.purge_all_data()
                                st.session_state.clear()
                                st.success("All data has been purged successfully!")
                                st.rerun()
                            except RuntimeError as e:
                                st.error(f"⚠️ Purge blocked: {e}")
                            except Exception as e:
                                st.error(f"❌ Purge failed: {e}")
                    else:
                        st.warning("Please type 'delete' to confirm.")

            with c2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state.show_maintenance_drawer = False
                    st.rerun()

            # JS Bridge: Live reactivity for purge confirmation
            components.html(
                f"""
                <script>
                const doc = window.parent.document;
                const check = () => {{
                    const inputs = doc.querySelectorAll('input[aria-label="Confirm Delete"]');
                    const buttons = doc.querySelectorAll('button');
                    const targetInput = Array.from(inputs).find(i => i.placeholder === "delete");
                    const targetBtn = Array.from(buttons).find(b => b.innerText.includes("Confirm"));

                    if (targetInput && targetBtn) {{
                        // 1. Set initial state based on current value
                        targetBtn.disabled = targetInput.value.toLowerCase() !== 'delete';
                        
                        // 2. Add listener for future changes
                        targetInput.addEventListener('input', (e) => {{
                            targetBtn.disabled = e.target.value.toLowerCase() !== 'delete';
                        }});
                    }}
                }};
                setInterval(check, 100);
                </script>
                """,
                height=0
            )

@st.fragment(run_every=5)
def _render_history_table():
    """
    Isolated fragment: only this function re-runs every 5 s.
    The sidebar, header, and report viewer are never touched between polls.
    """
    st.subheader("📂 Report History")
    processed_dir = "data/processed"

    all_runs = orchestrator.data_manager.list_run_history(limit=30)

    in_progress = any(r.get("status") in ("triggered", "running") for r in all_runs)
    # When nothing is in-flight, st.fragment still renders on user interactions;
    # the run_every timer simply keeps the table refreshed passively.

    STATUS_EMOJI = {
        "triggered": "🟡 Triggered",
        "running":   "🔵 Running",
        "succeeded": "🟢 Succeeded",
        "failed":    "🔴 Failed",
    }

    if all_runs:
        h1, h2, h3, h4, h5, h6 = st.columns([1, 4, 2, 3, 2, 2], vertical_alignment="center")
        h1.markdown("**S.No.**")
        h2.markdown("**Run ID**")
        h3.markdown("**Status**")
        h4.markdown("**Date Range**")
        h5.markdown("**Triggered On**")
        h6.markdown("**Download**")
        st.markdown("<hr style='margin: 0; padding: 0;'>", unsafe_allow_html=True)

        for row_idx, run in enumerate(all_runs, start=1):
            run_id  = run["run_id"]
            status  = run.get("status", "succeeded")
            badge   = STATUS_EMOJI.get(status, status)

            # --- Date range ---
            date_range_str = "-"
            try:
                if run_id.startswith("custom_"):
                    parts = run_id.split('_')
                    if len(parts) >= 3:
                        s = datetime.strptime(parts[1], "%Y%m%d")
                        e = datetime.strptime(parts[2], "%Y%m%d")
                        date_range_str = f"{s.strftime('%b %d')} - {e.strftime('%b %d %Y')}"
                elif "-W" in run_id:
                    year, week = run_id.split("-W")
                    week_start = datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
                    date_range_str = f"{week_start.strftime('%b %d')} - {(week_start + timedelta(days=6)).strftime('%b %d %Y')}"
                elif run.get("start_date") and run.get("end_date"):
                    s = datetime.fromisoformat(run["start_date"])
                    e = datetime.fromisoformat(run["end_date"])
                    date_range_str = f"{s.strftime('%b %d')} - {e.strftime('%b %d %Y')}"
            except Exception:
                pass

            # --- Triggered-at ---
            triggered_label = "-"
            if run.get("triggered_at"):
                try:
                    triggered_label = datetime.fromisoformat(run["triggered_at"]).strftime("%b %d, %Y %I:%M %p")
                except Exception:
                    triggered_label = run["triggered_at"][:16]

            # --- Email file ---
            email_path = os.path.join(processed_dir, f"pulse_email_{run_id}.html")
            has_file   = os.path.exists(email_path)

            c1, c2, c3, c4, c5, c6 = st.columns([1, 4, 2, 3, 2, 2], vertical_alignment="center")
            with c1: st.markdown(f"**{row_idx}**")
            with c2:
                if has_file:
                    st.markdown(f'<a href="/?run_id={run_id}" target="_self" style="text-decoration:underline">{run_id}</a>', unsafe_allow_html=True)
                else:
                    st.markdown(run_id)
            with c3: st.markdown(badge)
            with c4: st.markdown(date_range_str)
            with c5: st.markdown(triggered_label)
            with c6:
                if has_file:
                    with open(email_path, 'r', encoding='utf-8') as fp:
                        st.download_button("⬇", fp.read(), file_name=f"pulse_email_{run_id}.html",
                                           mime="text/html", key=f"dl_html_{run_id}")
                else:
                    st.caption("—")
            st.markdown("<hr style='margin: 0; padding: 0;'>", unsafe_allow_html=True)
    else:
        st.caption("No historical reports found yet. Generate your first pulse report to get started.")


# --- Main Content Area ---
if 'latest_result' in st.session_state:
    res = st.session_state['latest_result']

    
    if st.button("←"):
        del st.session_state['latest_result']
        st.query_params.clear()
        st.rerun()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("📧 Draft Email Report")
            
        email_path = res.get('artifacts', {}).get('email_html', '')
        if email_path and os.path.exists(email_path):
            with open(email_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            components.html(html_content, height=600, scrolling=True)

            st.download_button(
                label="Download HTML Email",
                data=html_content,
                file_name=os.path.basename(email_path),
                mime="text/html"
            )

    with col2:
        st.header("📤 Send Report")
        target_email = st.text_input("Enter recipient email:")
        if st.button("Send Email", use_container_width=True):
            if target_email and email_path and os.path.exists(email_path):
                with st.spinner("Sending email..."):
                    success = EmailService.send_email(
                        to_email=target_email,
                        subject=f"Weekly App Review Pulse - {datetime.now().strftime('%B %d, %Y')}",
                        html_content=html_content
                    )
                    if success:
                        st.balloons()
                        st.success("Email successfully sent!")
                    else:
                        st.error("Failed to send email. Please check your SMTP configuration.")
            elif not target_email:
                st.warning("Please enter a valid email address.")
            else:
                st.warning("No email report available to send.")

        st.divider()
        st.header("📊 Run Details")
        st.json({
            "Run ID": res.get("run_id"),
            "Reviews Processed": res["reviews_count"],
            "Themes Identified": res["themes_count"],
            "Date Range": f"{start_date} to {end_date}"
        })
else:
    st.info("Select a date range and click 'Generate Pulse Report' to get started.")
    _render_history_table()
