import os
import uvicorn
import external_variables as ext_vars
from strands import Agent
from strands.models import BedrockModel
from strands.session import SnapshotSessionManager
from strands_dynamodb_storage import DynamoDBStorage
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get environment variables for model configuration
MODEL_ID = os.getenv("MODEL_ID")
AWS_REGION = os.getenv("AWS_REGION")
AGENT_TABLE_NAME = os.getenv("AGENT_TABLE_NAME")

# Initialize FastAPI app
app = FastAPI(title="Agent Gateway")

storage_backend = DynamoDBStorage(
    table_name=AGENT_TABLE_NAME, 
    region_name=AWS_REGION,
    ttl_seconds=604800
)

@app.post("/generate")
async def generate_text(request: ext_vars.Request):
    try:
        # Initialize the Bedrock model wrapper
        bedrock_model = BedrockModel(
            model_id=MODEL_ID,
            region_name=AWS_REGION,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        # Initialize the session manager with DynamoDB storage
        session_manager = SnapshotSessionManager(
            session_id=request.session_id, 
            storage=storage_backend
        )
        
        # Instantiate the agent using the configured model
        agent = Agent(
            model=bedrock_model,
            session_manager=session_manager,
            system_prompt=request.system_prompt
        )
        
        # Invoke the model
        result = await agent.invoke_async(request.current_message)
        
        return {
            "role": "assistant",
            "content": [{"text": str(result)}]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent invocation failed: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)