import streamlit as st
import os
from datetime import datetime, timedelta
from src.orchestrator import PulseOrchestrator
import streamlit.components.v1 as components

st.set_page_config(page_title="Groww Pulse Report", page_icon="📈", layout="wide")

st.title("🌱 Groww - Weekly App Review Pulse")
st.markdown("Automated sentiment analysis and executive reporting for app store reviews.")

# Sidebar for configuration
with st.sidebar:
    st.header("Pipeline Configuration")
    
    # Date Range Selection
    start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=7))
    end_date = st.date_input("End Date", value=datetime.now())
    
    force_run = st.checkbox("Force Run (Bypass Idempotency)", value=False)
    
    if st.button("🚀 Generate Pulse Report", use_container_width=True):
        if start_date > end_date:
            st.error("Error: Start date must be before end date.")
        else:
            with st.spinner("Executing Pulse Pipeline..."):
                orchestrator = PulseOrchestrator()
                # Convert date to datetime
                dt_start = datetime.combine(start_date, datetime.min.time())
                dt_end = datetime.combine(end_date, datetime.max.time())
                
                result = orchestrator.run_pipeline(
                    force=force_run,
                    start_date=dt_start,
                    end_date=dt_end
                )
                
                if result["status"] == "success":
                    st.success(f"Pipeline completed! Processed {result['reviews_count']} reviews.")
                    st.session_state['latest_result'] = result
                else:
                    st.error(f"Pipeline failed: {result.get('error', 'Unknown error')}")

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
                # In a real app, this would trigger an SMTP call or SendGrid API
                st.info(f"Simulation: Sending report to {target_email}...")
                st.balloons()
                st.success(f"Email successfully 'sent' to {target_email}!")
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
