import requests
import json
import re
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import uvicorn

# ==================== CONFIGURATION ====================
AZURE_ENDPOINT = "https://cs-chatbot-foundry.services.ai.azure.com/"
AZURE_API_KEY = "key"
DEPLOYMENT_NAME = "gpt-4o-mini"  # Change to your deployment name

# ==================== DATA MODELS ====================
class ChatRequest(BaseModel):
    user_id: str
    query: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    intent: str
    actions: List[str]
    ticket_id: Optional[str] = None

# ==================== MOCK BACKENDS ====================
orders = {
    "ORD-12345": {"status": "Shipped", "tracking": "1Z999AA10123456784", "date": "2026-04-28"},
    "ORD-12346": {"status": "Processing", "date": "2026-05-02"}
}

tickets = []
ticket_counter = 1000

def get_order(order_num):
    return orders.get(order_num)

def create_ticket(customer_id, issue, desc):
    global ticket_counter
    ticket_counter += 1
    ticket = {"id": f"TKT-{ticket_counter}", "customer": customer_id, "issue": issue, "desc": desc, "status": "Open"}
    tickets.append(ticket)
    return ticket

# ==================== AZURE AI CLIENT ====================
class AzureAIClient:
    def __init__(self):
        self.headers = {"Content-Type": "application/json", "api-key": AZURE_API_KEY}
    
    def chat(self, query, context=""):
        url = f"{AZURE_ENDPOINT}openai/v1/responses?api-version=2024-12-01-preview"
        payload = {
            "model": DEPLOYMENT_NAME,
            "input": [
                {"role": "system", "content": "You are a helpful customer support assistant. Keep responses short."},
                {"role": "user", "content": f"Query: {query}\nContext: {context}"}
            ],
            "max_output_tokens": 300
        }
        try:
            resp = requests.post(url, headers=self.headers, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("output", [{}])[0].get("content", "")
        except:
            pass
        return None

azure_client = AzureAIClient()

# ==================== INTENT DETECTION ====================
def detect_intent(query):
    q = query.lower()
    if any(word in q for word in ["order", "status", "track", "where"]):
        return "CheckOrderStatus"
    if any(word in q for word in ["refund", "money back", "return"]):
        return "RequestRefund"
    if any(word in q for word in ["broken", "not working", "issue", "problem"]):
        return "TechnicalSupport"
    if any(word in q for word in ["agent", "human", "speak", "talk"]):
        return "SpeakToAgent"
    return "General"

def extract_order_number(text):
    match = re.search(r'ORD[- ]?(\d+)', text, re.IGNORECASE)
    return f"ORD-{match.group(1)}" if match else None

# ==================== RESPONSE GENERATION ====================
def generate_response(intent, query, user_id):
    actions = []
    ticket_id = None
    
    if intent == "CheckOrderStatus":
        order_num = extract_order_number(query)
        if order_num:
            order = get_order(order_num)
            if order:
                actions.append(f"Checked status for {order_num}")
                response = f" Order {order_num} is **{order['status']}**. Track: {order.get('tracking', 'N/A')}"
            else:
                response = f" Order {order_num} not found. Please check the number."
        else:
            response = "Please provide your order number (e.g., ORD-12345)"
    
    elif intent == "RequestRefund":
        ticket = create_ticket(user_id, "Refund", query)
        ticket_id = ticket["id"]
        actions.append(f"Created refund ticket {ticket_id}")
        response = f" Refund request created. Ticket {ticket_id} - agent will review within 24h"
    
    elif intent == "TechnicalSupport":
        ticket = create_ticket(user_id, "Tech Support", query)
        ticket_id = ticket["id"]
        actions.append(f"Created support ticket {ticket_id}")
        response = f" Support ticket {ticket_id} created. Specialist will contact you soon"
    
    elif intent == "SpeakToAgent":
        ticket = create_ticket(user_id, "Escalation", query)
        ticket_id = ticket["id"]
        actions.append(f"Escalated to agent via {ticket_id}")
        response = f" Escalated to human agent. Ticket #{ticket_id} - agent will join shortly"
    
    else:
        actions.append("Logged for general assistance")
        response = f"Thanks for reaching out! I'll help with: {query[:100]}..."
    
    # Try to enhance with Azure AI
    ai_response = azure_client.chat(query, f"Intent: {intent}")
    if ai_response:
        response = ai_response
    
    return response, actions, ticket_id

# ==================== FASTAPI APP ====================
app = FastAPI(title="AI Customer Support Bot")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

sessions = {}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        intent = detect_intent(req.query)
        response, actions, ticket_id = generate_response(intent, req.query, req.user_id)
        
        session_id = req.session_id or f"sess_{datetime.now().timestamp()}"
        sessions[session_id] = sessions.get(session_id, []) + [{"q": req.query, "r": response}]
        
        return ChatResponse(response=response, intent=intent, actions=actions, ticket_id=ticket_id)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/health")
async def health():
    return {"status": "ok", "sessions": len(sessions)}

@app.get("/tickets/{customer}")
async def get_tickets(customer: str):
    return [t for t in tickets if t["customer"] == customer]

# ==================== RUN SERVER ====================
if __name__ == "__main__":
    print(" Chatbot running at http://localhost:8000")
    print(" API Docs: http://localhost:8000/docs")
    print("\n Try these commands:")
    print('   curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d \'{"user_id":"1","query":"Where is my order ORD-12345?"}\'')
    print('   curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d \'{"user_id":"1","query":"I want a refund"}\'')
    uvicorn.run(app, host="0.0.0.0", port=8000)