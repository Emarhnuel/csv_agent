import sys
import os
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
import pandas as pd
import time
import shutil

# Add the absolute path to the rag_agent's source directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rag_agent_path = os.path.join(project_root, "rag_agent", "src")
rag_agent_env_path = os.path.join(project_root, "rag_agent", ".env")
sys.path.append(rag_agent_path)

# Load environment variables from the rag_agent .env file
load_dotenv(dotenv_path=rag_agent_env_path)

# Import after path is set
from rag_agent.crew import UB04ClaimBuilderCrew
from output_handler import capture_output

# Define which task types should be shown in the UI logs
IMPORTANT_TASK_TYPES = [
    "extract",
    "analyze",
    "generate",
    "verify",
    "review",
    "complete"
]

# Define key milestone messages to highlight
MILESTONE_MARKERS = [
    "extracting patient data",
    "analyzing claim",
    "generating form",
    "validating data",
    "reviewing claim",
    "completed"
]

class MinimalLogFilter:
    """Filter class that only allows important logs to pass through."""
    
    def __init__(self, output_container):
        self.output_container = output_container
        self.milestones_shown = set()
    
    def write_milestone(self, message, emoji="✨"):
        """Write an important milestone message to the output with emoji."""
        if message not in self.milestones_shown:
            self.output_container.write(f"{emoji} {message}")
            self.milestones_shown.add(message)
    
    def track_progress(self, message):
        """Track progress based on keywords in message."""
        msg_lower = message.lower()
        
        # Check for milestone keywords and add appropriate emoji
        if "extracting" in msg_lower or "extract" in msg_lower:
            self.write_milestone("Extracting patient data...", "🔎")
        elif "analyzing" in msg_lower or "analyze" in msg_lower:
            self.write_milestone("Analyzing claim information...", "📊")
        elif "generate" in msg_lower or "creating" in msg_lower or "filling" in msg_lower:
            self.write_milestone("Generating UB-04 form...", "📝")
        elif "validat" in msg_lower or "verify" in msg_lower:
            self.write_milestone("Validating claim data...", "✓")
        elif "review" in msg_lower:
            self.write_milestone("Reviewing final claim...", "📋")
        elif "complet" in msg_lower or "finish" in msg_lower or "done" in msg_lower:
            self.write_milestone("Processing complete", "✅")

def get_available_patients():
    """
    Get a list of all patient names in the CSV file.
    
    Returns:
        list: List of full patient names (FirstName LastName)
    """
    csv_path = os.path.join(project_root, "rag_agent", "knowledge", "ub04_claims.csv")
    try:
        df = pd.read_csv(csv_path)
        # Create full names by combining first and last names
        full_names = [f"{row['PatientFirstName']} {row['PatientLastName']}" 
                      for _, row in df.iterrows()]
        return full_names
    except Exception as e:
        st.error(f"Error loading patient data: {e}")
        return []

def run_claim_builder_crew(patient_name: str, output_container=None):
    """
    Run the UB-04 Claim Builder Crew with the given parameters.

    Args:
        patient_name: The patient's name to search for.
        output_container: Optional Streamlit container to capture output.

    Returns:
        The result of the crew's execution.
    """
    # Prepare inputs
    inputs = {'patient_name': patient_name}
    
    # Initialize a new crew instance each time to avoid state conflicts
    crew = UB04ClaimBuilderCrew()

    # When running with streamlit output container, use reduced logging
    if output_container:
        # Create a logger filter
        log_filter = MinimalLogFilter(output_container)
        
        # Display starting milestone
        log_filter.write_milestone(f"🔍 Processing UB-04 claim for patient: {patient_name}", "🔍")
        
        # Run with output capturing and reduced verbosity
        with capture_output(output_container):
            # We're not using callbacks as they're not supported
            # Instead, we rely on the StreamlitProcessOutput filtering
            result = crew.crew().kickoff(inputs=inputs)
            
        # Add completion message
        log_filter.write_milestone(f"✅ Claim processing complete for {patient_name}", "✅")
    else:
        # Run with standard output (for console/debugging)
        result = crew.crew().kickoff(inputs=inputs)

    # Return the result
    return result

def process_multiple_patients(patients, progress_callback=None, status_callback=None):
    """
    Process multiple patients sequentially and handle the PDF copying.
    
    Args:
        patients: List of patient names to process
        progress_callback: Function to call with progress updates (0-1)
        status_callback: Function to call with status message updates
        
    Returns:
        List of dictionaries with processing results for each patient
    """
    results = []
    total_patients = len(patients)
    
    # Ensure the output directory exists for copied PDFs
    output_dir = os.path.join(project_root, "rag_agent", "src", "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Setup overall batch processing container if status_callback is available
    if status_callback:
        status_callback(f"🚀 Starting batch processing for {total_patients} patients")
    
    for i, patient in enumerate(patients):
        # Update progress
        current_progress = i / total_patients
        if progress_callback:
            progress_callback(current_progress)
        
        # Update status with patient number and percentage
        percent_complete = int(current_progress * 100)
        if status_callback:
            status_callback(f"⏳ Processing patient {i+1}/{total_patients} ({percent_complete}%): {patient}")
        
        try:
            # Run the crew for this patient
            result = run_claim_builder_crew(patient_name=patient)
            
            # Check for the generated PDF
            report_path = get_pdf_report_path()
            
            if report_path and report_path.exists():
                # Make a copy with unique name
                safe_name = patient.replace(" ", "_").lower()
                copy_path = os.path.join(output_dir, f"ub04_claim_{safe_name}.pdf")
                
                # Copy the file
                shutil.copy2(report_path, copy_path)
                
                # Read the PDF content for the user to download
                with open(copy_path, "rb") as file:
                    pdf_content = file.read()
                
                # Add to results with success message
                results.append({
                    "patient": patient,
                    "path": copy_path,
                    "content": pdf_content,
                    "success": True
                })
                
                # Update status with success message
                if status_callback:
                    status_callback(f"✅ Successfully processed claim for {patient}")
            else:
                # Record failure
                results.append({
                    "patient": patient,
                    "success": False,
                    "error": "PDF not generated"
                })
                
                # Update status with failure message
                if status_callback:
                    status_callback(f"❌ Failed to generate PDF for {patient}")
                    
        except Exception as e:
            # Record error
            results.append({
                "patient": patient,
                "success": False,
                "error": str(e)
            })
            
            # Update status with error message
            if status_callback:
                status_callback(f"❌ Error processing {patient}: {str(e)}")
            
        # Brief pause between patients
        if i < total_patients - 1:
            time.sleep(1)
    
    # Update progress to complete
    if progress_callback:
        progress_callback(1.0)
    
    # Final status update
    if status_callback:
        status_callback(f"✅ Batch processing complete! Processed {total_patients} patients.")
    
    # Return the results
    return results

def get_pdf_report_path():
    """
    Check for the generated PDF report and return its path.

    Returns:
        Path: The path to the PDF report, or None if not found.
    """
    # Path to the PDF report in the rag_agent's output directory
    pdf_path = Path(os.path.join(project_root, "rag_agent", "src", "output", "ub04_claim_filled.pdf"))
    
    if pdf_path.exists():
        return pdf_path
    else:
        return None
