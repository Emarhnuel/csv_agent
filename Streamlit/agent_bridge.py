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

    # Run with or without output capturing
    if output_container:
        with capture_output(output_container):
            result = crew.crew().kickoff(inputs=inputs)
    else:
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
    
    # Ensure the output directory exists for copied PDFs
    output_dir = os.path.join(project_root, "rag_agent", "src", "output")
    os.makedirs(output_dir, exist_ok=True)
    
    for i, patient in enumerate(patients):
        # Update progress
        if progress_callback:
            progress_callback(i / len(patients))
        
        # Update status
        if status_callback:
            status_callback(f"Processing {i+1}/{len(patients)}: {patient}")
        
        try:
            # Run the crew for this patient
            result = run_claim_builder_crew(patient_name=patient)
            
            # Check for the generated PDF
            report_path = get_pdf_report_path()
            
            if report_path and report_path.exists():
                # Create a unique filename for this patient
                safe_name = patient.replace(" ", "_").lower()
                patient_pdf_path = os.path.join(output_dir, f"ub04_claim_{safe_name}.pdf")
                
                # Copy the PDF to the new path but ensure original is fully written
                time.sleep(1)  # Brief pause to ensure PDF is fully written
                shutil.copy2(report_path, patient_pdf_path)
                
                # Read the PDF content
                with open(patient_pdf_path, "rb") as file:
                    pdf_content = file.read()
                
                # Store success
                results.append({
                    "patient": patient,
                    "path": patient_pdf_path,
                    "content": pdf_content,
                    "success": True
                })
            else:
                # Record failure
                results.append({
                    "patient": patient,
                    "success": False,
                    "error": "PDF not generated"
                })
                
            # Brief pause between patients to avoid conflicts
            if i < len(patients) - 1:
                time.sleep(2)
                
        except Exception as e:
            # Record error
            results.append({
                "patient": patient,
                "success": False,
                "error": str(e)
            })
    
    # Update final progress
    if progress_callback:
        progress_callback(1.0)
    
    # Return all results
    return results

def get_pdf_report_path():
    """
    Check for the generated PDF report and return its path.

    Returns:
        Path: The path to the PDF report, or None if not found.
    """
    # Look in the output directory inside the rag_agent src directory
    report_path = Path(os.path.join(project_root, "rag_agent", "src", "output", "ub04_claim_filled.pdf"))
    
    if report_path.exists():
        return report_path
    else:
        return None
