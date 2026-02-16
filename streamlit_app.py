import streamlit as st
import os
from datetime import datetime, timedelta
from src.orchestrator import PulseOrchestrator
from src.email_service import EmailService
import streamlit.components.v1 as components

st.set_page_config(page_title="Groww Pulse Report", page_icon="📈", layout="wide")

@st.cache_resource
def get_orchestrator():
    return PulseOrchestrator()

orchestrator = get_orchestrator()

st.title("🌱 Groww - Weekly App Review Pulse")
st.markdown("Automated sentiment analysis and executive reporting for app store reviews.")

# Sidebar for configuration
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
                # Uses the cached orchestrator from module level
                # Convert date to datetime
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

    # --- Maintenance Section (Senior Engineer Refinement) ---
    # --- Maintenance Section (Senior Engineer Structural Refinement) ---
    st.divider()
    st.header("🛠️ Maintenance")

    # This 'Senior' approach uses a standard button to avoid the popover chevron
    # AND allow us to catch the click event in Python to reset the state.
    if st.button("🗑️ Purge All History", use_container_width=True):
        # Reset the input value whenever the button is clicked to start fresh
        st.session_state.purge_val = ""
        st.session_state.show_maintenance_drawer = not st.session_state.get('show_maintenance_drawer', False)

    if st.session_state.get('show_maintenance_drawer'):
        with st.container(border=True):
            st.error("⚠️ Critical Action: Purging all data.")
            st.write("To confirm, please type **delete** below:")
            
            # 1. The Input: Keyed to purge_val
            st.text_input("Confirm Delete", placeholder="delete", label_visibility="collapsed", key="purge_val")
            
            # 2. Buttons: Secure via Python check + visual reactivity via JS
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔥 Confirm Full Purge", type="primary", disabled=st.session_state.get("purge_val", "").lower() != "delete", use_container_width=True):
                    with st.spinner("Purging all data..."):
                        if orchestrator.purge_all_data():
                            st.session_state.clear()
                            st.success("All data has been purged successfully!")
                            st.rerun()
            with c2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.show_maintenance_drawer = False
                    st.rerun()
            
            # 3. JS Bridge: Provides the 'Live Reactivity' (Senior UX)
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
                // Run periodically to catch the container rendering
                setInterval(check, 300);
                </script>
                """,
                height=0
            )

# Main content area
if 'latest_result' in st.session_state:
    res = st.session_state['latest_result']
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📧 Draft Email Report")
        email_path = res['artifacts']['email_html']
        if os.path.exists(email_path):
            with open(email_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Display HTML in a scrollable container
            components.html(html_content, height=600, scrolling=True)
            
            st.download_button(
                label="📥 Download HTML Email",
                data=html_content,
                file_name=os.path.basename(email_path),
                mime="text/html"
            )
    
    with col2:
        st.header("📤 Send Report")
        target_email = st.text_input("Enter recipient email:")
        if st.button("📧 Send Email", use_container_width=True):
            if target_email:
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
            else:
                st.warning("Please enter a valid email address.")
        
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
    
    # Show previous reports if any
    st.subheader("Recent Artifacts")
    processed_dir = "data/processed"
    if os.path.exists(processed_dir):
        files = [f for f in os.listdir(processed_dir) if f.endswith('.md')]
        if files:
            st.write(f"Found {len(files)} historical reports in {processed_dir}")
        else:
            st.write("No historical reports found yet.")
