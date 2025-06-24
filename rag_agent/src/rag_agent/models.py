from pydantic import BaseModel, Field
from typing import List, Optional

class Facility(BaseModel):
    name: str = Field(..., description="Name of the facility")
    address: str = Field(..., description="Address of the facility")

class Patient(BaseModel):
    first_name: str = Field(..., description="Patient's first name")
    last_name: str = Field(..., description="Patient's last name")
    dob: str = Field(..., description="Patient's date of birth")
    sex: str = Field(..., description="Patient's sex")
    mrn: str = Field(..., description="Patient's Medical Record Number")

class Visit(BaseModel):
    admission_date: str = Field(..., description="Admission date")
    discharge_date: str = Field(..., description="Discharge date")
    patient_control_number: str = Field(..., description="Patient control number")

class Payer(BaseModel):
    name: str = Field(..., description="Payer's name")
    id: str = Field(..., description="Payer's ID")

class Diagnoses(BaseModel):
    primary: str = Field(..., description="Primary diagnosis code")
    secondary: Optional[str] = Field(None, description="Secondary diagnosis code")

class AttendingPhysician(BaseModel):
    npi: str = Field(..., description="Attending Physician's NPI")

class Physicians(BaseModel):
    attending: AttendingPhysician = Field(..., description="Attending physician details")

class RevenueLine(BaseModel):
    revenue_code: str = Field(..., description="Revenue code")
    hcpcs_code: Optional[str] = Field(None, description="HCPCS code")
    units: int = Field(..., description="Number of units")
    charge: float = Field(..., description="Charge for the revenue line")

class UB04Claim(BaseModel):
    """Model representing the entire UB-04 claim data structure."""
    facility: Facility
    patient: Patient
    visit: Visit
    payer: Payer
    bill_type: str = Field(..., description="Type of bill")
    diagnoses: Diagnoses
    physicians: Physicians
    revenue_lines: List[RevenueLine] = Field(..., description="List of revenue lines")
    total_charge: float = Field(..., description="Total charge for the claim")