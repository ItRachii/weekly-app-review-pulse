import streamlit as st
import requests
import os
from datetime import datetime, timedelta
import streamlit.components.v1 as components
from PIL import Image

# --- App Config ---
API_BASE_URL = "http://localhost:8000/api/v1"

groww_icon = Image.open("assets/groww_logo.png")
st.set_page_config(page_title="Groww Pulse Report", page_icon=groww_icon, layout="wide")

# --- Groww Brand Theme CSS ---
st.markdown("""
<style>
    /* ===== Groww Brand Colors =====
       Groww Blue:            #5367F5
       Groww Green (Logo):    #08F6B6
       Groww Green (Primary): #00D09C
       Groww Accent Blue A:   #B1D0FB
       Groww Accent Blue B:   #E5F4FD
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


# --- Helper: API calls ---
def api_get(endpoint):
    """GET request to the API."""
    try:
        resp = requests.get(f"{API_BASE_URL}{endpoint}", timeout=30)
        resp.raise_for_status()
        return resp
    except requests.ConnectionError:
        st.error("⚠️ Cannot connect to API server. Make sure `python main_api.py` is running on port 8000.")
        return None
    except requests.RequestException as e:
        st.error(f"API error: {e}")
        return None


def api_post(endpoint, json_data=None):
    """POST request to the API."""
    try:
        resp = requests.post(f"{API_BASE_URL}{endpoint}", json=json_data, timeout=120)
        resp.raise_for_status()
        return resp
    except requests.ConnectionError:
        st.error("⚠️ Cannot connect to API server. Make sure `python main_api.py` is running on port 8000.")
        return None
    except requests.HTTPException as e:
        st.error(f"API error: {e}")
        return None


def api_delete(endpoint, headers=None):
    """DELETE request to the API."""
    try:
        resp = requests.delete(f"{API_BASE_URL}{endpoint}", headers=headers, timeout=30)
        resp.raise_for_status()
        return resp
    except requests.ConnectionError:
        st.error("⚠️ Cannot connect to API server. Make sure `python main_api.py` is running on port 8000.")
        return None
    except requests.RequestException as e:
        st.error(f"API error: {e}")
        return None


# --- Page Header ---
logo_col, title_col = st.columns([0.08, 0.92], vertical_alignment="center")
with logo_col:
    st.image("assets/groww_logo.png", width=80)
with title_col:
    st.title("Groww - Weekly App Review Pulse")
    st.markdown("Automated sentiment analysis and executive reporting for app store reviews.")

# --- Sidebar ---
with st.sidebar:
    st.header("Pipeline Configuration")

    # Date Range Selection
    start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=7))
    end_date = st.date_input("End Date", value=datetime.now())

    if st.button("🚀 Generate Pulse Report", use_container_width=True):
        if start_date > end_date:
            st.error("Error: Start date must be before end date.")
        else:
            with st.spinner("Executing Pulse Pipeline..."):
                resp = api_post("/trigger", json_data={
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "force": False
                })
                if resp:
                    result = resp.json()
                    if result.get("status") == "success":
                        st.success(f"Pipeline completed! Processed {result['reviews_count']} reviews.")
                        st.session_state['latest_result'] = result
                    else:
                        st.error(f"Pipeline failed: {result.get('error', 'Unknown error')}")

    # --- Maintenance Section ---
    st.divider()
    st.header("🛠️ Maintenance")

    if st.button("🗑️ Purge All History", use_container_width=True):
        st.session_state.purge_val = ""
        st.session_state.show_maintenance_drawer = not st.session_state.get('show_maintenance_drawer', False)

    if st.session_state.get('show_maintenance_drawer'):
        with st.container(border=True):
            st.error("⚠️ Critical Action: Purging all data.")
            st.write("To confirm, please type **delete** below:")

            st.text_input("Confirm Delete", placeholder="delete", label_visibility="collapsed", key="purge_val")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔥 Confirm Full Purge", type="primary", disabled=st.session_state.get("purge_val", "").lower() != "delete", use_container_width=True):
                    with st.spinner("Purging all data..."):
                        resp = api_delete("/purge", headers={"X-Confirm-Purge": "delete"})
                        if resp:
                            st.session_state.clear()
                            st.success("All data has been purged successfully!")
                            st.rerun()
            with c2:
                if st.button("❌ Cancel", use_container_width=True):
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
                    const targetBtn = Array.from(buttons).find(b => b.innerText.includes("Confirm Full Purge"));

                    if (targetInput && targetBtn) {{
                        targetInput.addEventListener('input', (e) => {{
                            targetBtn.disabled = e.target.value.toLowerCase() !== 'delete';
                        }});
                    }}
                }};
                setInterval(check, 300);
                </script>
                """,
                height=0
            )

# --- Main Content Area ---
if 'latest_result' in st.session_state:
    res = st.session_state['latest_result']

    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("📧 Draft Email Report")
        # Get email HTML content via API
        email_filename = None
        if res.get('artifacts', {}).get('email_html'):
            email_filename = os.path.basename(res['artifacts']['email_html'])

        if email_filename:
            content_resp = api_get(f"/reports/{email_filename}")
            if content_resp:
                html_content = content_resp.text
                components.html(html_content, height=600, scrolling=True)

                st.download_button(
                    label="📥 Download HTML Email",
                    data=html_content,
                    file_name=email_filename,
                    mime="text/html"
                )

    with col2:
        st.header("📤 Send Report")
        target_email = st.text_input("Enter recipient email:")
        if st.button("📧 Send Email", use_container_width=True):
            if target_email and email_filename:
                with st.spinner("Sending email..."):
                    resp = api_post("/send-email", json_data={
                        "to_email": target_email,
                        "report_file": email_filename
                    })
                    if resp:
                        result = resp.json()
                        if result.get("status") == "sent":
                            st.balloons()
                            st.success(f"Email successfully sent to {target_email}!")
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

    # --- Report History via API ---
    st.subheader("📂 Report History")
    reports_resp = api_get("/reports")

    if reports_resp:
        data = reports_resp.json()
        reports = data.get("reports", [])

        md_reports = [r for r in reports if r["type"] == "markdown"]
        html_reports = [r for r in reports if r["type"] == "html"]

        if md_reports or html_reports:
            if md_reports:
                st.markdown("**📝 Pulse Notes (Markdown)**")
                for r in md_reports:
                    mod_time = datetime.fromisoformat(r["modified_at"])
                    date_label = mod_time.strftime("%b %d, %Y  •  %I:%M %p")

                    col_name, col_date, col_dl = st.columns([3, 3, 1])
                    with col_name:
                        st.markdown(f"📄 `{r['filename']}`")
                    with col_date:
                        st.caption(f"🕒 {date_label}")
                    with col_dl:
                        content_resp = api_get(f"/reports/{r['filename']}")
                        if content_resp:
                            st.download_button("⬇", content_resp.text, file_name=r['filename'], mime="text/markdown", key=f"dl_md_{r['filename']}")

            if html_reports:
                st.markdown("**📧 Email Reports (HTML)**")
                for r in html_reports:
                    mod_time = datetime.fromisoformat(r["modified_at"])
                    date_label = mod_time.strftime("%b %d, %Y  •  %I:%M %p")

                    col_name, col_date, col_dl = st.columns([3, 3, 1])
                    with col_name:
                        st.markdown(f"📧 `{r['filename']}`")
                    with col_date:
                        st.caption(f"🕒 {date_label}")
                    with col_dl:
                        content_resp = api_get(f"/reports/{r['filename']}")
                        if content_resp:
                            st.download_button("⬇", content_resp.text, file_name=r['filename'], mime="text/html", key=f"dl_html_{r['filename']}")
        else:
            st.caption("No historical reports found yet. Generate your first pulse report to get started.")
