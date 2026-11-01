import os
import boto3
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Initialize FastAPI app
app = FastAPI(title="Agent Gateway")

try:
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    )
except Exception as e:
    print(f"Error initializing Bedrock client: {e}")
    bedrock_client = None

# Individual message item format matching Amazon Nova's expected schema
class MessageContent(BaseModel):
    text: str

class ChatMessage(BaseModel):
    role: str  # Must alternatingly be "user" or "assistant"
    content: List[MessageContent]

# Request schema accepting the entire message thread history
class MultiTurnRequest(BaseModel):
    messages: List[ChatMessage]
    max_tokens: int = 512
    temperature: float = 0.7

@app.post("/generate")
async def generate_text(request: MultiTurnRequest):
    if not bedrock_client:
        raise HTTPException(status_code=500, detail="AWS Bedrock client not initialized.")

    # Target model set to Amazon Nova Lite
    model_id = "us.amazon.nova-lite-v1:0"

    # Map the FastAPI Pydantic models directly into Nova's expected dictionary payload format
    formatted_messages = [
        {
            "role": msg.role,
            "content": [{"text": item.text} for item in msg.content]
        }
        for msg in request.messages
    ]

    # Structure payload for Amazon Nova Converse API / Text generation
    body = json.dumps({
        "inferenceConfig": {
            "maxTokens": request.max_tokens,
            "temperature": request.temperature
        },
        "messages": formatted_messages
    })

    try:
        response = bedrock_client.invoke_model(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json"
        )
        
        # Parse the Nova response structure
        response_body = json.loads(response.get("body").read())
        output_text = response_body["output"]["message"]["content"][0]["text"]
        
        # Extract content from Nova's response payload
        output_text = response_body["output"]["message"]["content"][0]["text"]
        
        return {
            "role": "assistant",
            "content": [{"text": output_text}]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bedrock Nova invocation failed: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)