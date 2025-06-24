import pandas as pd
import chromadb
from typing import Type, Callable
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
import json
import os
from dotenv import load_dotenv
# Import the specific embedding function we will use
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

# Load environment variables to get the API key
load_dotenv()

class CSVKnowledgeToolInput(BaseModel):
    """Input schema for CSVKnowledgeTool."""
    patient_name: str = Field(..., description="The full name of the patient to search for in the CSV.")

class CSVKnowledgeTool(BaseTool):
    name: str = "RAG CSV Knowledge Tool"
    description: str = (
        "Searches a CSV file of patient claims to find data for a specific patient. "
        "Uses a RAG pipeline with OpenAI embeddings for accurate semantic search."
    )
    args_schema: Type[BaseModel] = CSVKnowledgeToolInput
    csv_path: str
    db_path: str = "db/chroma"
    collection_name: str = ""
    df: pd.DataFrame = None
    collection: chromadb.Collection = None
    embedding_function: Callable = None

    def __init__(self, csv_path: str, **kwargs):
        # Pass csv_path to BaseTool for Pydantic validation
        super().__init__(csv_path=csv_path, **kwargs)
        self.csv_path = csv_path
        
        # The tool now creates its own embedding function internally
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set. Please add it to your .env file.")
        model_name = "text-embedding-3-large"  # Using a modern, cost-effective model
        self.embedding_function = OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name=model_name
        )

        # Derive a collection name that encodes the model, so different
        # embedding sizes live in separate collections (prevents
        #   "embedding dimension X does not match collection dimensionality Y")
        safe_model_name = model_name.replace("/", "_").replace("-", "_")
        self.collection_name = f"ub04_claims_{safe_model_name}"

        self._setup_rag()

    def _setup_rag(self):
        """
        Sets up the RAG pipeline. This involves loading the CSV, initializing the 
        vector database, and indexing the data if it hasn't been already.
        """
        # 1. Load the CSV data into a pandas DataFrame
        self.df = pd.read_csv(self.csv_path)
        # Ensure name columns are strings for consistent processing
        self.df['PatientFirstName'] = self.df['PatientFirstName'].astype(str)
        self.df['PatientLastName'] = self.df['PatientLastName'].astype(str)

        # 2. Initialize a persistent ChromaDB client
        if not os.path.exists(self.db_path):
            os.makedirs(self.db_path)
        client = chromadb.PersistentClient(path=self.db_path)
        
        # 3. Get or create the collection, passing the internal embedding function
        self.collection = client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function
        )

        # 4. Check if the collection is already populated to avoid re-indexing
        if self.collection.count() == 0:
            print(f"ChromaDB collection '{self.collection_name}' is empty. Indexing CSV data with OpenAI embeddings...")
            
            # Create a descriptive document for each row to improve search quality
            documents = []
            for index, row in self.df.iterrows():
                doc = (
                    f"Patient Name: {row['PatientFirstName']} {row['PatientLastName']}. "
                    f"Medical Record Number: {row['MedicalRecordNumber']}. "
                    f"Payer: {row['PrimaryPayerName']}. "
                    f"Admission Date: {row['AdmissionDate']}."
                )
                documents.append(doc)
            
            # Add the documents to the collection.
            self.collection.add(
                documents=documents,
                ids=[str(i) for i in self.df.index] # Use row index as a unique ID
            )
            print("Indexing complete.")

    def _run(self, patient_name: str) -> str:
        """
        The main execution method. It takes a patient's name, searches the 
        vector database, and returns the full data for the best match as a JSON string.
        """
        print(f"RAG Tool: Searching for patient '{patient_name}' with OpenAI embeddings...")
        
        # 1. Query the collection to find the most similar document
        results = self.collection.query(
            query_texts=[patient_name],
            n_results=1
        )

        # 2. Handle cases where no results are found
        if not results or not results['ids'][0]:
            return f"Error: No patient found matching the name '{patient_name}'."

        # 3. Get the ID of the best match, which is our row index
        best_match_id = results['ids'][0][0]
        
        # 4. Retrieve the full data row from the original DataFrame
        patient_data_row = self.df.loc[int(best_match_id)]
        
        # 5. Convert the row to a dictionary and then to a JSON string for the agent
        return patient_data_row.to_json()
