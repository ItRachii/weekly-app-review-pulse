import streamlit as st
import os
from datetime import datetime, timedelta
import streamlit.components.v1 as components
from PIL import Image
from src.orchestrator import PulseOrchestrator
from src.email_service import EmailService

# --- App Config ---
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


@st.cache_resource
def get_orchestrator():
    return PulseOrchestrator()


orchestrator = get_orchestrator()

# --- Page Header ---
logo_col, title_col = st.columns([0.08, 0.92], vertical_alignment="center")
with logo_col:
    import base64
    with open("assets/groww_logo.png", "rb") as img_file:
        logo_b64 = base64.b64encode(img_file.read()).decode()
    st.markdown(f'<img src="data:image/png;base64,{logo_b64}" width="80">', unsafe_allow_html=True)
with title_col:
    st.title("Groww - Weekly App Review Pulse")
    st.markdown("Automated sentiment analysis and executive reporting for app store reviews.")

# --- Sidebar ---
with st.sidebar:
    st.header("Pipeline Configuration")

    # Date Range Selection
    start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=7))
    end_date = st.date_input("End Date", value=datetime.now())

    if st.button("Generate Pulse Report", use_container_width=True):
        if start_date > end_date:
            st.error("Error: Start date must be before end date.")
        else:
            with st.spinner("Executing Pulse Pipeline..."):
                dt_start = datetime.combine(start_date, datetime.min.time())
                dt_end = datetime.combine(end_date, datetime.max.time())

                result = orchestrator.run_pipeline(
                    start_date=dt_start,
                    end_date=dt_end
                )

                if result["status"] == "success":
                    st.success(f"Pipeline completed! Processed {result['reviews_count']} reviews.")
                    st.session_state['latest_result'] = result
                else:
                    st.error(f"Pipeline failed: {result.get('error', 'Unknown error')}")

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
                            if orchestrator.purge_all_data():
                                st.session_state.clear()
                                st.success("All data has been purged successfully!")
                                st.rerun()
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

# --- Main Content Area ---
if 'latest_result' in st.session_state:
    res = st.session_state['latest_result']

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
                        subject=f"[GROWW] Weekly App Review Pulse - {datetime.now().strftime('%B %d, %Y')}",
                        html_content=html_content
                    )
                    if success:
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

    # --- Report History ---
    st.subheader("📂 Report History")
    processed_dir = "data/processed"
    if os.path.exists(processed_dir):
        md_files = sorted(
            [f for f in os.listdir(processed_dir) if f.endswith('.md')],
            key=lambda f: os.path.getmtime(os.path.join(processed_dir, f)),
            reverse=True
        )
        html_files = sorted(
            [f for f in os.listdir(processed_dir) if f.endswith('.html')],
            key=lambda f: os.path.getmtime(os.path.join(processed_dir, f)),
            reverse=True
        )

        if md_files or html_files:
            if md_files:
                st.markdown("**📝 Pulse Notes (Markdown)**")
                for f in md_files:
                    fpath = os.path.join(processed_dir, f)
                    mod_time = datetime.fromtimestamp(os.path.getmtime(fpath))
                    date_label = mod_time.strftime("%b %d, %Y  •  %I:%M %p")

                    col_name, col_date, col_dl = st.columns([3, 3, 1])
                    with col_name:
                        st.markdown(f"📄 `{f}`")
                    with col_date:
                        st.caption(f"🕒 {date_label}")
                    with col_dl:
                        with open(fpath, 'r', encoding='utf-8') as fp:
                            st.download_button("⬇", fp.read(), file_name=f, mime="text/markdown", key=f"dl_md_{f}")

            if html_files:
                st.markdown("**📧 Email Reports (HTML)**")
                for f in html_files:
                    fpath = os.path.join(processed_dir, f)
                    mod_time = datetime.fromtimestamp(os.path.getmtime(fpath))
                    date_label = mod_time.strftime("%b %d, %Y  •  %I:%M %p")

                    col_name, col_date, col_dl = st.columns([3, 3, 1])
                    with col_name:
                        st.markdown(f"📧 `{f}`")
                    with col_date:
                        st.caption(f"🕒 {date_label}")
                    with col_dl:
                        with open(fpath, 'r', encoding='utf-8') as fp:
                            st.download_button("⬇", fp.read(), file_name=f, mime="text/html", key=f"dl_html_{f}")
        else:
            st.caption("No historical reports found yet. Generate your first pulse report to get started.")
    else:
        st.caption("No historical reports found yet. Generate your first pulse report to get started.")
