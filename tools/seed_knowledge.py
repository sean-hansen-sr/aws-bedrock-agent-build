import os
import boto3
import json
import uuid
from strands import tool
from strands.vended_memory_stores.bedrock_knowledge_base import BedrockKnowledgeBaseStore
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get environment variables for model configuration
DATA_SOURCE_BUCKET=os.getenv("DATA_SOURCE_BUCKET")

s3 = boto3.client("s3")

@tool
def seed_knowledge(application: str = "", triage: str = "") -> str:
    """Save a new troubleshooting guide to the knowledge base S3 bucket.
    
    ONLY call this tool when the user explicitly asks to save, record, 
    document, or publish a solution to the knowledge base. Do NOT call 
    this tool during normal Q&A or general troubleshooting.

    Args:
        application: The name of the system or application being documented (e.g., "Payment Service")..
        triage: The step-by-step instructions to remediate the issue.
    """
    if not application.strip() or not triage.strip():
        return (
            "STOP: Missing required details. Ask the user for both the application name "
            "and the triage steps before calling this tool again."
        )
    try:
        unique_id = uuid.uuid4().hex[:4]
        safe_app = application.strip().lower().replace(" ", "-")
        s3_key = f"agent-memories/{safe_app}-{unique_id}.txt"
        body = f"Application: {application}\n\nTriage Steps:\n{triage}"

        s3.put_object(
            Bucket=DATA_SOURCE_BUCKET,
            Key=s3_key,
            Body=body.encode("utf-8"),
            ContentType="text/plain"
        )

        data = {
            "matadataAttributes": {
                "document_type": "triage article",
                "application": safe_app,
                "tags": ["RAG", safe_app]
            }
        }

        s3.put_object(
            Bucket=DATA_SOURCE_BUCKET,
            Key=f"{s3_key}.metadata.json",
            Body=json.dumps(data, indent=4),
            ContentType="application/json"
        )

        return f"DONE: Saved to {s3_key}. Task complete—respond to the user now."
    except Exception as e:
        return f"ERROR: {str(e)}. Do not retry—report this error to the user."