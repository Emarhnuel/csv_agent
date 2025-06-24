#!/usr/bin/env python
import sys
import opik
from rag_agent.crew import UB04ClaimBuilderCrew
from opik.integrations.crewai import track_crewai
from dotenv import load_dotenv


load_dotenv()

opik.configure(use_local=False)



track_crewai(project_name="csv_agent")




# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information


def run():
    """
    Run the UB-04 claim-builder crew.
    """
    # Provide the initial input for the crew.
    # The 'patient_name' is used by the first task to fetch the initial data.
    inputs = {
        'patient_name': 'Patel Nicholas', 
    }
    
    try:
        # Instantiate and run the crew.
        UB04ClaimBuilderCrew().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")



