import fitz  # PyMuPDF
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Dict, Any
import os

class PDFFormFillerInput(BaseModel):
    """Input schema for the PDF Form Filler Tool."""
    claim_data: Dict[Any, Any] = Field(..., description="A dictionary containing the UB-04 claim data.")

class PDFFormFillerTool(BaseTool):
    name: str = "UB-04 PDF Form Filler"
    description: str = "Fills a fillable UB-04 PDF form using a dictionary of claim data."
    args_schema: Type[BaseModel] = PDFFormFillerInput
    template_path: str = r"c:\Users\user\Downloads\RAG_ai_agent\rag_agent\template\ub-40-.pdf"
    output_path: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../output/ub04_claim_filled.pdf"))   

    def _run(self, claim_data: Dict[Any, Any]) -> str:
        try:
            # Debug: Print the received data structure
            print(f"Received claim data: {claim_data}")
            
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

            # Open the PDF template
            doc = fitz.open(self.template_path)
            if not doc:
                return f"Error: Could not open template at {self.template_path}"
                
            page = doc.load_page(0)  # Load the first page
            
            # Debug: Print available fields in PDF
            print("Available form fields:")
            for widget in page.widgets():
                print(f"Field name: {widget.field_name}, Type: {widget.field_type}")

            # --- Create the mapping from PDF fields to our data ---
            # This dictionary maps the PDF's internal field names to the values from the claim data.
            value_mapping = {}
            
            # Map facility data
            if "facility" in claim_data:
                value_mapping['FacilityName'] = claim_data["facility"].get("name", "")
                value_mapping['FacilityAddress'] = claim_data["facility"].get("address", "")
            
            # Map patient data
            if "patient" in claim_data:
                value_mapping['PatientFirstName'] = claim_data["patient"].get("first_name", "")
                value_mapping['PatientLastName'] = claim_data["patient"].get("last_name", "")
                value_mapping['PatientDOB'] = claim_data["patient"].get("dob", "")
                value_mapping['PatientSex'] = claim_data["patient"].get("sex", "")
                value_mapping['MedicalRecordNumber'] = claim_data["patient"].get("mrn", "")
            
            # Map visit data
            if "visit" in claim_data:
                value_mapping['PatientControlNumber'] = claim_data["visit"].get("patient_control_number", "")
                value_mapping['AdmissionDate'] = claim_data["visit"].get("admission_date", "")
                value_mapping['DischargeDate'] = claim_data["visit"].get("discharge_date", "")
            
            # Map payer data
            if "payer" in claim_data:
                value_mapping['PrimaryPayerName'] = claim_data["payer"].get("name", "")
                value_mapping['PrimaryPayerID'] = claim_data["payer"].get("id", "")
            
            # Map billing data
            if "bill_type" in claim_data:
                value_mapping['BillType'] = claim_data.get("bill_type", "")
            
            # Map diagnoses data
            if "diagnoses" in claim_data:
                value_mapping['PrimaryDiagnosisCode'] = claim_data["diagnoses"].get("primary", "")
                value_mapping['SecondaryDiagnosisCode1'] = claim_data["diagnoses"].get("secondary", "")
            
            # Map physician data
            if "physicians" in claim_data and "attending" in claim_data["physicians"]:
                value_mapping['AttendingPhysicianNPI'] = claim_data["physicians"]["attending"].get("npi", "")
            
            # Map total charge
            if "total_charge" in claim_data:
                value_mapping['TotalCharge'] = str(claim_data.get("total_charge", 0.0))
            
            # Map revenue lines
            if "revenue_lines" in claim_data and len(claim_data["revenue_lines"]) > 0:
                if len(claim_data["revenue_lines"]) > 0:
                    value_mapping['RevenueCode1'] = str(claim_data["revenue_lines"][0].get("revenue_code", ""))
                    value_mapping['HCPCSCode1'] = str(claim_data["revenue_lines"][0].get("hcpcs_code", "") or "")
                    value_mapping['Units1'] = str(claim_data["revenue_lines"][0].get("units", 0))
                    value_mapping['Charges1'] = str(claim_data["revenue_lines"][0].get("charge", 0.0))
                
                if len(claim_data["revenue_lines"]) > 1:
                    value_mapping['RevenueCode2'] = str(claim_data["revenue_lines"][1].get("revenue_code", ""))
                    value_mapping['HCPCSCode2'] = str(claim_data["revenue_lines"][1].get("hcpcs_code", "") or "")
                    value_mapping['Units2'] = str(claim_data["revenue_lines"][1].get("units", 0))
                    value_mapping['Charges2'] = str(claim_data["revenue_lines"][1].get("charge", 0.0))
            
            # Debug: Print our mapping
            print("Value mapping:")
            for key, value in value_mapping.items():
                print(f"{key}: {value}")
            
            # --- Fill the PDF ---
            successful_updates = 0
            for widget in page.widgets():
                if widget.field_name in value_mapping:
                    try:
                        # Set the field's value
                        widget.field_value = value_mapping[widget.field_name]
                        # Apply the change
                        widget.update()
                        print(f"Updated field {widget.field_name} with value {value_mapping[widget.field_name]}")
                        successful_updates += 1
                    except Exception as e:
                        print(f"Error updating field {widget.field_name}: {e}")

            # Save the filled PDF
            try:
                doc.save(self.output_path, garbage=4, deflate=True, clean=True)
                print(f"PDF saved to {self.output_path}")
                doc.close()
                return f"Successfully filled PDF ({successful_updates} fields updated) and saved to '{self.output_path}'"
            except Exception as e:
                print(f"Error saving PDF: {e}")
                return f"Error saving PDF: {e}"

        except Exception as e:
            print(f"Error in PDF filling tool: {e}")
            return f"An error occurred while filling the PDF: {e}"