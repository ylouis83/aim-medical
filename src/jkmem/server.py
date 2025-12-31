import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from jkmem.agent import MemoryAgent
from jkmem.llm import call_llm
from jkmem.memory_backends import get_memory_backend
from jkmem.medical.report_parser import ReportService
from jkmem.graph_store import get_graph_store

app = FastAPI(title="AskBob Medical Agent", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for dev; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
agent: Optional[MemoryAgent] = None
report_service: Optional[ReportService] = None
graph_store: Optional[Any] = None

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"
    metadata: Optional[Dict[str, Any]] = None

class ReportRequest(BaseModel):
    report_text: str
    user_id: str = "default"
    patient_id: str
    title: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    global agent, report_service, graph_store
    try:
        memory = get_memory_backend()
        # Initialize Agent
        agent = MemoryAgent(memory=memory, llm_fn=call_llm)
        
        try:
            graph_store = get_graph_store()
        except Exception as exc:
            graph_store = None
            print(f"Graph store initialization skipped: {exc}")

        report_service = ReportService(memory_backend=memory, graph_store=graph_store)
        
        print("Backend initialized successfully.")
    except Exception as e:
        print(f"Error initializing backend: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    if graph_store:
        graph_store.close()

@app.get("/health")
async def health_check():
    return {"status": "ok", "agent_initialized": agent is not None}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        result = agent.respond(
            message=request.message,
            user_id=request.user_id,
            metadata=request.metadata
        )
        # Handle both old str return (just in case) and new dict return
        if isinstance(result, str):
             return {"response": result, "memories": []}
        return {"response": result["content"], "memories": result["memories"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload_report")
async def upload_report(request: ReportRequest):
    if not report_service:
        raise HTTPException(status_code=503, detail="Report service not initialized")
    
    try:
        result = report_service.parse_and_store(
            user_id=request.user_id,
            report_text=request.report_text,
            patient_id=request.patient_id,
            # document_id can be auto-generated
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("JKMEM_HOST", "0.0.0.0")
    port = int(os.getenv("JKMEM_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
