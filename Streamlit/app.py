__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import time
import shutil


# Add the absolute path to the rag_agent's source directory
# The Streamlit app is in RAG_ai_agent/Streamlit, so we go up one level
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rag_agent_path = os.path.join(project_root, "rag_agent", "src")
rag_agent_env_path = os.path.join(project_root, "rag_agent", ".env")
sys.path.append(rag_agent_path)

# Load environment variables from the rag_agent's .env file
load_dotenv(dotenv_path=rag_agent_env_path)


# Import from the agent bridge
from agent_bridge import run_claim_builder_crew, get_pdf_report_path, get_available_patients

# Configure the page
st.set_page_config(
    page_title="UB-04 Claim Builder",
    page_icon="📄",
    layout="wide"
)

# Initialize session state variables
if "api_keys_set" not in st.session_state:
    st.session_state.api_keys_set = True

if "processed_pdfs" not in st.session_state:
    st.session_state.processed_pdfs = []

if "processing_complete" not in st.session_state:
    st.session_state.processing_complete = False
    
# Store the available patients in session state to avoid reloading
if "available_patients" not in st.session_state:
    st.session_state.available_patients = get_available_patients()

# Main header
st.markdown("<h1 style='text-align: center; margin-bottom: 20px;'>📄 UB-04 Claim Builder</h1>", unsafe_allow_html=True)

# Sidebar for information
with st.sidebar:
    st.title("Information")

    # About section
    with st.expander("About", expanded=True):
        st.markdown("""
        **UB-04 Claim Builder** automates the creation of medical claim forms.

        This agent uses CrewAI to:
        - Extract patient data from a source file.
        - Audit the data for compliance.
        - Generate a final, accurate UB-04 claim form as a PDF.

        Powered by [CrewAI](https://crewai.com).
        """)
    
    # API Configuration info
    with st.expander("API Configuration", expanded=False):
        st.info("This application is using API keys configured in the rag_agent/.env file.")
        
        # Show which API keys are configured (without showing the actual keys)
        if os.getenv("OPENAI_API_KEY"):
            st.success("✅ OPENAI_API_KEY is configured")
        else:
            st.error("❌ OPENAI_API_KEY is not configured in the .env file")
            
        if os.getenv("OPENROUTER_API_KEY"):
            st.success("✅ OPENROUTER_API_KEY is configured")
        else:
            st.error("❌ OPENROUTER_API_KEY is not configured in the .env file")
            
        if os.getenv("GOOGLE_API_KEY"):
            st.success("✅ GOOGLE_API_KEY is configured")
        else:
            st.error("❌ GOOGLE_API_KEY is not configured in the .env file")
            
# Create tabs for Single Patient and Multiple Patients processing
tab1, tab2 = st.tabs(["Single Patient", "Multiple Patients"])

# Tab 1: Single Patient Processing
with tab1:
    st.header("Process Individual Patient")
    
    # Patient name selection
    patient_name = st.selectbox(
        "Select Patient",
        options=st.session_state.available_patients,
        index=None,
        placeholder="Choose a patient from the list",
        help="Select a patient to generate a UB-04 claim form."
    )
    
    # Run analysis button
    run_button = st.button("🚀 Build Claim Form", type="primary", disabled=not patient_name, key="single_patient_button")

    # Check if we should run the analysis
    if run_button and patient_name:
        # Create a progress bar and status message
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("Initializing claim processing...")
        
        # Create a hidden container for the detailed logs
        log_container = st.container()
        with st.expander("Processing Details", expanded=False):
            output_container = st.container()
            
        with st.spinner("Building UB-04 Claim..."):
            try:
                # Update progress
                progress_bar.progress(0.2)
                status_text.text("Extracting patient data...")
                
                # Run the crew with detailed output hidden in collapsed expander
                result = run_claim_builder_crew(patient_name=patient_name, output_container=output_container)
                
                # Update progress
                progress_bar.progress(0.8)
                status_text.text("Generating PDF form...")
                
                # Check for the generated PDF report
                report_path = get_pdf_report_path()

                if report_path and report_path.exists():
                    # Update progress to complete
                    progress_bar.progress(1.0)
                    status_text.text("Claim form successfully generated!")
                    
                    # Read the PDF content for downloading
                    with open(report_path, "rb") as file:
                        pdf_content = file.read()

                    # Show success message and download button
                    st.success(f"✅ Successfully generated claim form for {patient_name}")
                    
                    # Download button
                    st.download_button(
                        label="📥 Download PDF Report",
                        data=pdf_content,
                        file_name=f"ub04_claim_{patient_name.replace(' ', '_').lower()}.pdf",
                        mime="application/pdf"
                    )
                else:
                    progress_bar.progress(1.0)
                    status_text.text("Failed to generate claim form.")
                    st.error("Could not find the generated PDF report. The crew may have failed to create it.")

            except Exception as e:
                progress_bar.progress(1.0)
                status_text.text("Error occurred during processing.")
                st.error(f"An error occurred: {str(e)}")

# Tab 2: Multiple Patients Processing
with tab2:
    st.header("Process Multiple Patients")
    
    # Multi-select patients
    selected_patients = st.multiselect(
        "Select Multiple Patients",
        options=st.session_state.available_patients,
        help="Select multiple patients to process one by one"
    )
    
    col1, col2 = st.columns([1, 1])
    
    # Run batch button
    with col1:
        batch_button = st.button("🚀 Process Selected Patients", type="primary", disabled=not selected_patients, key="batch_button")
    
    # Clear results button
    with col2:
        clear_button = st.button("🗑️ Clear Results", type="secondary", disabled=len(st.session_state.processed_pdfs) == 0, key="clear_button")
        
    if clear_button:
        # Clear the processed PDFs and reset the processing complete flag
        st.session_state.processed_pdfs = []
        st.session_state.processing_complete = False
        st.experimental_rerun()
    
    if batch_button and selected_patients:
        # Create a progress bar and status container
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("Preparing to process patients...")
        
        # Create a hidden container for logs - only show this in the expandable section
        with st.expander("Detailed Processing Logs", expanded=False):
            log_expander = st.container()
        
        # Clear any previous results
        st.session_state.processed_pdfs = []
        st.session_state.processing_complete = False
        
        # Process each patient
        for i, patient in enumerate(selected_patients):
            # Update progress
            progress = (i) / len(selected_patients)
            progress_bar.progress(progress)
            status_text.text(f"Processing {i+1}/{len(selected_patients)}: {patient}")
            
            # Create a container for this patient's processing output - within the collapsed expander
            with log_expander:
                st.write(f"**Processing patient: {patient}**")
                patient_output = st.container()
            
            try:
                # Run the crew with output captured in the patient's container (hidden in the expander)
                result = run_claim_builder_crew(patient_name=patient, output_container=patient_output)
                
                # Check for the generated PDF report
                report_path = get_pdf_report_path()
                
                if report_path and report_path.exists():
                    # Make a copy with unique name
                    safe_name = patient.replace(" ", "_").lower()
                    copy_path = os.path.join(project_root, "rag_agent", "src", "output", f"ub04_claim_{safe_name}.pdf")
                    
                    # Copy the file
                    shutil.copy2(report_path, copy_path)
                    
                    # Read the PDF content for the user to download
                    with open(copy_path, "rb") as file:
                        pdf_content = file.read()
                    
                    # Store the processed PDF info
                    st.session_state.processed_pdfs.append({
                        "patient": patient,
                        "path": str(copy_path),
                        "content": pdf_content,
                        "success": True
                    })
                    
                    # Log success in the hidden container
                    with log_expander:
                        st.success(f"Successfully processed {patient}")
                else:
                    # Record failure
                    st.session_state.processed_pdfs.append({
                        "patient": patient,
                        "success": False,
                        "error": "PDF not generated"
                    })
                    
                    # Log failure in the hidden container
                    with log_expander:
                        st.error(f"Failed to process {patient}: PDF not generated")
                
                # Brief pause between patients to avoid rate limiting
                if i < len(selected_patients) - 1:
                    time.sleep(2)  # Increased wait time to ensure completion
                    
            except Exception as e:
                # Record error
                st.session_state.processed_pdfs.append({
                    "patient": patient,
                    "success": False,
                    "error": str(e)
                })
                
                # Log error in the hidden container
                with log_expander:
                    st.error(f"Error processing {patient}: {str(e)}")
        
        # Complete the progress bar
        progress_bar.progress(1.0)
        status_text.text(f"Completed processing {len(selected_patients)} patients")
        
        # Set the processing complete flag
        st.session_state.processing_complete = True
        
    # Display results section if there are processed PDFs
    if len(st.session_state.processed_pdfs) > 0:
        st.subheader("Processing Results")
        
        # Calculate success rate
        success_count = sum(1 for result in st.session_state.processed_pdfs if result["success"])
        
        # Show success metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Successfully Processed", success_count)
        with col2:
            st.metric("Failed", len(st.session_state.processed_pdfs) - success_count)
        
        # Show download section only if there are successful PDFs
        if success_count > 0:
            st.subheader("Download Reports")
            
            # Determine how many columns to display per row
            columns_per_row = 3
            
            # Loop through the results in groups to create rows of columns
            successful_pdfs = [pdf for pdf in st.session_state.processed_pdfs if pdf["success"]]
            for i in range(0, len(successful_pdfs), columns_per_row):
                # Create a row of columns
                cols = st.columns(columns_per_row)
                
                # Process patients for this row
                for j in range(columns_per_row):
                    idx = i + j
                    if idx < len(successful_pdfs):
                        result = successful_pdfs[idx]
                        
                        # Get the PDF content or read it from the path if needed
                        pdf_content = result.get("content")
                        if pdf_content is None and "path" in result:
                            try:
                                with open(result["path"], "rb") as file:
                                    pdf_content = file.read()
                                    # Update the content in session state
                                    result["content"] = pdf_content
                            except Exception as e:
                                st.error(f"Could not read PDF for {result['patient']}: {str(e)}")
                                continue
                        
                        with cols[j]:
                            st.write(f"**{result['patient']}**")
                            
                            # Use a unique key for each download button
                            download_key = f"download_{result['patient']}_{idx}"
                            
                            # Download button for this patient's PDF
                            st.download_button(
                                label=f"📥 Download PDF",
                                data=pdf_content,
                                file_name=f"ub04_claim_{result['patient'].replace(' ', '_').lower()}.pdf",
                                mime="application/pdf",
                                key=download_key
                            )
            
            # Add a download all button
            if len(successful_pdfs) > 1:
                st.write("---")
                st.write("**Download All PDFs as a ZIP**")
                
                # Create a ZIP file containing all PDFs
                import io
                import zipfile
                
                # Create a BytesIO object for the zip file
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
                    for pdf in successful_pdfs:
                        if "content" in pdf and pdf["content"]:
                            safe_name = pdf["patient"].replace(" ", "_").lower()
                            zip_file.writestr(f"ub04_claim_{safe_name}.pdf", pdf["content"])
                
                # Offer the ZIP file for download
                st.download_button(
                    label="📥 Download All PDFs (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="all_ub04_claims.zip",
                    mime="application/zip",
                    key="download_all_zip"
                )

# Footer
st.markdown("---")  
st.caption("Made with ❤️ using CrewAI and Streamlit")
