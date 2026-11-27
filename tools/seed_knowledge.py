import os
import re
import boto3
import json
import uuid
from difflib import SequenceMatcher
from datetime import datetime, timezone
from strands import tool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get environment variables for model configuration
DATA_SOURCE_BUCKET=os.getenv("DATA_SOURCE_BUCKET")
SEED_KNOWLEDGE_PATH=os.getenv("SEED_KNOWLEDGE_PATH")
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID")
DATA_SOURCE_ID = os.getenv("DATA_SOURCE_ID")

s3 = boto3.client("s3")
bedrock_agent = boto3.client("bedrock-agent")

def _slugify_string(name: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip().lower()).strip("-")
    return f"{clean or 'document'}"

def _extract_attr_str(attrs: dict, field: str) -> str:
    # Safely extract string values from Bedrock structured metadataAttributes.
    raw = attrs.get(field, "")
    if isinstance(raw, dict):
        return str(raw.get("value", {}).get("stringValue", "")).strip()
    return str(raw).strip()

def _extract_attr_list(attrs: dict, field: str) -> list[str]:
    # Safely extract list values from Bedrock structured metadataAttributes.
    raw = attrs.get(field, [])
    if isinstance(raw, dict):
        values = raw.get("value", {}).get("stringListValue", [])
        return [str(v).strip() for v in values if str(v).strip()]
    if isinstance(raw, list):
        return [str(v).strip() for v in raw if str(v).strip()]
    return []

def _similarity(a: str, b: str) -> float:
    a_clean, b_clean = a.strip().lower(), b.strip().lower()
    if a_clean == b_clean:
        return 1.0
    # Boost score if one phrase is contained inside the other
    if a_clean in b_clean or b_clean in a_clean:
        return 0.85
    return SequenceMatcher(None, a_clean, b_clean).ratio()

def _app_matches(
    target_app: str, existing_app: str, existing_aliases: list[str], threshold: float = 0.70
) -> bool:
    # Return True if no app filter was provided, or if target_app matches existing_app or any alias.
    if not target_app.strip():
        return True

    candidates = [existing_app, *existing_aliases]
    return any(
        candidate and _similarity(target_app, candidate) >= threshold
        for candidate in candidates
    )


def _find_similar_entries(application: str, symptom: str, threshold: float = 0.65) -> list[dict]:
    # Return existing sidecars whose 'symptom' and 'application' closely matches the target value.
    prefix = f"{SEED_KNOWLEDGE_PATH.strip('/')}/" if SEED_KNOWLEDGE_PATH else ""
    paginator = s3.get_paginator("list_objects_v2")
    matches = []

    for page in paginator.paginate(Bucket=DATA_SOURCE_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".txt.metadata.json"):
                continue
            
            body = s3.get_object(Bucket=DATA_SOURCE_BUCKET, Key=key)["Body"].read().decode("utf-8")
            attrs = json.loads(body).get("metadataAttributes", {})
            
            existing_app = _extract_attr_str(attrs, "application")
            existing_aliases = _extract_attr_list(attrs, "aliases")
            existing_symptom = _extract_attr_str(attrs, "symptom")
            
            if not existing_symptom:
                continue

            symptom_score = _similarity(symptom, existing_symptom)
            # app_matches = not application or _similarity(application, existing_app) >= 0.70

            #if app_matches and symptom_score >= threshold:
            if _app_matches(application, existing_app, existing_aliases) and symptom_score >= threshold:
                matches.append({
                    "key": key.removesuffix(".metadata.json"),
                    "application": existing_app,
                    "aliases": existing_aliases,
                    "symptom": existing_symptom,
                    "score": round(symptom_score, 2),
                })

    return sorted(matches, key=lambda item: item["score"], reverse=True)

@tool
def check_existing_knowledge(application: str = "", symptom: str = "") -> str:
    """Read-only check for existing or closely matching troubleshooting guides in S3.

    ALWAYS call this tool BEFORE calling `seed_knowledge`.
    """
    if not symptom.strip():
        return "MISSING_INPUT: Ask the user for the application name, symptom, and triage steps first."

    matches = _find_similar_entries(application, symptom)
    if not matches:
        return "NO_MATCHES: No closely matching entries found. Proceed to call `seed_knowledge`."

    formatted = "\n".join(
        f"- application='{m['application']}' | symptom='{m['symptom']}' | key='{m['key']}' (similarity={m['score']})"
        for m in matches[:5]
    )
    return (
        f"MATCHES_FOUND for symptom='{symptom}':\n{formatted}\n\n"
        "Ask the user whether they want to:"
        "1) Overwrite one of these existing keys (pass the `target_key` to `seed_knowledge`) or"
        "2) Create a separate new file anyway."
    )

@tool
def seed_knowledge(
    application: str = "", 
    aliases: str = "", 
    symptom: str ="", 
    triage: str = "",
    target_key: str | None = None
) -> str:
    """
    Save a troubleshooting guide to the knowledge base S3 bucket.

    Only call this AFTER `check_existing_knowledge` has run (and after user confirmation if matches were found).

    Args:
        application: The name of the system or application being documented (e.g., "Payment Service")..
        aliases: A comma seperated list of application aliases that could be used when asking questions
        symptom: The issue being documented
        triage: The step-by-step instructions to remediate the issue.
        target_key: Existing S3 key to overwrite if the user confirms updating a matched entry.
    """
    if not application.strip() or not symptom.strip() or not triage.strip():
        return (
            """STOP: Missing required details. Ask the user for the application name, 
            the symptom, and the triage steps before calling this tool again."""
        )

    try:
        prefix = f"{SEED_KNOWLEDGE_PATH.strip('/')}/" if SEED_KNOWLEDGE_PATH else ""
        unique_id = uuid.uuid4().hex[:8]
        now = datetime.now(timezone.utc)
        date_path = now.strftime("%Y%m%d")
        
        s3_key = target_key or (
            f"{prefix}{_slugify_string(application)}-{date_path}-{unique_id}.txt" 
            if SEED_KNOWLEDGE_PATH 
            else f"{_slugify_string(application)}-{date_path}-{unique_id}.txt"
        )
        body = f"Application: {application}\nAliases: {aliases}\n\nSymptom: {symptom}\n\nTriage Steps:\n{triage}"
        
        s3.put_object(
            Bucket=DATA_SOURCE_BUCKET,
            Key=s3_key,
            Body=body.encode("utf-8"),
            ContentType="text/plain"
        )

        alias_list = [alias.strip() for alias in aliases.split(",") if aliases.strip()]

        metadata_attrs = {
            "document_type": "triage article",
            "doc_version": "1.0.0",
            "is_public": "true",
            "application": application,
            "aliases": alias_list,
            "symptom": symptom,
            "tags": ["RAG", _slugify_string(application)]
        }

        if alias_list:
            metadata_attrs["aliases"] = alias_list

        data = {"metadataAttributes": metadata_attrs}

        s3.put_object(
            Bucket=DATA_SOURCE_BUCKET,
            Key=f"{s3_key}.metadata.json",
            Body=json.dumps(data, indent=4),
            ContentType="application/json"
        )

        # return f"DONE: Saved to {s3_key}. Task complete—respond to the user now."
    # except Exception as e:
        # return f"ERROR: {str(e)}. Do not retry—report this error to the user."

        ingest_response = bedrock_agent.ingest_knowledge_base_documents(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=DATA_SOURCE_ID,
            documents=[
                {
                    "content": {
                        "dataSourceType": "S3",
                        "s3": {"s3Location": {"uri": f"s3://{DATA_SOURCE_BUCKET}/{s3_key}"}},
                    },
                    "metadata": {
                        "type": "S3_LOCATION",
                        "s3Location": {
                            "uri": f"s3://{DATA_SOURCE_BUCKET}/{s3_key}.metadata.json"
                        },
                    },
                }
            ],
        )

        doc_status = ingest_response["documentDetails"][0]["status"]

        return (
            f"""DONE: Saved to {s3_key} and queued direct ingestion (Status:
            {doc_status}). Task complete—respond to the user now."""
        )
    except Exception as e:
        return f"ERROR: {str(e)}. Do not retry—report this error to the user."