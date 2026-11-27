import os
import boto3
from strands import tool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get environment variables for model configuration
AWS_REGION = os.getenv("AWS_REGION")
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID")

kb_runtime = boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)

@tool
def search_knowledge(query: str) -> str:
    """Search the support knowledge base for troubleshooting guides and application documentation.
    
    Args:
        query: The technical question, application name, or symptom to search for.
    """
    response = kb_runtime.retrieve(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "managedSearchConfiguration": {"numberOfResults": 3}
        }
    )

    results = [
        r["content"]["text"]
        for r in response.get("retrievalResults", [])
        if r.get("score", 0) >= 0.55
    ]

    if not results:
        return "No relevant troubleshooting guides found in the knowledge base. Answer using general knowledge or ask for clarification."
    return "\n\n---\n\n".join(results)