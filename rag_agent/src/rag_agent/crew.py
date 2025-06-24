from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.memory import LongTermMemory
from crewai.memory.storage.ltm_sqlite_storage import LTMSQLiteStorage
from .tools.csv_tool import CSVKnowledgeTool
from .tools.pdf_tool import PDFFormFillerTool 
from dotenv import load_dotenv
from crewai import LLM 
from rag_agent.models import UB04Claim 
import os 


load_dotenv() 

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

os.environ["GOOGLE_API_KEY"] = "GOOGLE_API_KEY"


# Configure custom storage location 
custom_storage_path = "./memory"
os.makedirs(custom_storage_path, exist_ok=True)


# Initialize the LLM
llm = LLM( 
    model="openai/gpt-4.1-2025-04-14",
    max_tokens=10000,
    temperature=0.0,
    verbose=True,
    seed=42,
)

llm2 = LLM(
    model="openai/o3-2025-04-16",
    max_tokens=10000,
    temperature=0.0, 
    verbose=True,
    seed=42,
)

llm3 = LLM(
    model="openrouter/google/gemini-2.5-pro-preview-05-06",
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    temperature=0.0,
    max_tokens=50000
)


# Initialize the tools. The CSV tool is now self-contained and only needs the path.

# Use absolute path for the CSV file - resolving relative to the project directory
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
csv_path = os.path.join(project_root, "knowledge", "ub04_claims.csv")

# Ensure the knowledge directory exists
knowledge_dir = os.path.join(project_root, "knowledge")
os.makedirs(knowledge_dir, exist_ok=True)

csv_tool = CSVKnowledgeTool(
    csv_path=csv_path
)

pdf_tool = PDFFormFillerTool()


@CrewBase
class UB04ClaimBuilderCrew():
    """Crew handling the end-to-end nursing-home UB-04 claim workflow."""

    # YAML configuration files for agents and tasks
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # ---------------- Agents ---------------- #
    @agent
    def ehr_interface_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['ehr_interface_specialist'],  # type: ignore[index]
            verbose=True,
            tools=[csv_tool], 
            max_rpm=30,
            max_iter=4,
            llm=llm
        )
    
    @agent
    def reporting_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['reporting_agent'],  # type: ignore[index]
            verbose=True,
            tools=[pdf_tool],  
            max_rpm=40,
            max_iter=4,
            llm=llm
        ) 

    # ---------------- Tasks ---------------- #
    @task
    def gather_encounter_data(self) -> Task:
        return Task(
            config=self.tasks_config['gather_encounter_data'],  # type: ignore[index]
            output_pydantic=UB04Claim
        )

    @task
    def generate_pdf_task(self) -> Task:
        return Task(
            config=self.tasks_config['generate_pdf_task'],  # type: ignore[index]
        )

    # ---------------- Crew ---------------- #
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            long_term_memory=LongTermMemory(
                storage=LTMSQLiteStorage(
                    db_path="memory/rag_memory.db"
                )
            ), 
            memory_config={
                "provider": "default",
            }
        )