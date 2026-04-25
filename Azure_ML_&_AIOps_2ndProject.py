import requests
import time
import logging
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

# ==================== CONFIG ====================
ML_ENDPOINT = "http://76f8e8bd-97c8-4a7f-ba85-32d69723c266.centralindia.azurecontainer.io/score"
ML_KEY = "key"
ALERT_THRESHOLD = 0.7  # Alert if failure probability > 70%

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== DATA MODEL ====================
class SensorData(BaseModel):
    MachineID: int
    Temperature: float
    Vibration: float
    Pressure: float
    Humidity: float
    Hour: int
    Day: int

# ==================== AZURE ML CLIENT ====================
def predict_failure(sensor: SensorData):
    """Call Azure ML endpoint"""
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {ML_KEY}"}
    
    # Prepare payload with Timestamp (required by your endpoint)
    payload = {
        "Inputs": {
            "input1": [{
                "Timestamp": datetime.now().isoformat(),
                "MachineID": str(sensor.MachineID),
                "Temperature": sensor.Temperature,
                "Vibration": sensor.Vibration,
                "Pressure": sensor.Pressure,
                "Humidity": sensor.Humidity,
                "Hour": sensor.Hour,
                "Day": sensor.Day
            }]
        },
        "GlobalParameters": {}
    }
    
    try:
        response = requests.post(ML_ENDPOINT, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            # Extract probability (adjust based on actual response format)
            prob = list(result.values())[0][0] if result else 0.5
            return float(prob)
        else:
            logger.error(f"ML Error: {response.status_code}")
            return 0.5
    except Exception as e:
        logger.error(f"Error: {e}")
        return 0.5

# ==================== ALERT SYSTEM ====================
def send_alert(machine_id: int, probability: float):
    """Send alert via email/SMS (mock)"""
    message = f" ALERT: Machine {machine_id} has {probability:.1%} failure risk!"
    logger.warning(message)
    
    # For real email, uncomment:
    # import smtplib
    # server.sendmail("alert@factory.com", "maintenance@company.com", message)
    
    # For real SMS, use Twilio or similar
    # from twilio.rest import Client
    # client.messages.create(body=message, to="+1234567890", from_="+1987654321")
    
    return True

# ==================== FASTAPI APP ====================
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

# Store recent predictions for dashboard
predictions = []

@app.post("/predict-failure")
async def predict(sensor: SensorData, background_tasks: BackgroundTasks):
    """Main prediction endpoint"""
    start = time.time()
    
    # Get prediction from Azure ML
    probability = predict_failure(sensor)
    latency = (time.time() - start) * 1000
    
    # Determine risk level
    if probability >= 0.85:
        risk = "CRITICAL"
        maintenance = True
    elif probability >= ALERT_THRESHOLD:
        risk = "HIGH"
        maintenance = True
    elif probability >= 0.4:
        risk = "MEDIUM"
        maintenance = False
    else:
        risk = "LOW"
        maintenance = False
    
    # Send alert if needed
    if probability >= ALERT_THRESHOLD:
        background_tasks.add_task(send_alert, sensor.MachineID, probability)
    
    # Store for dashboard
    predictions.append({
        "time": datetime.now().isoformat(),
        "machine": sensor.MachineID,
        "probability": probability,
        "risk": risk
    })
    
    return {
        "machine_id": sensor.MachineID,
        "failure_probability": round(probability, 3),
        "risk_level": risk,
        "requires_maintenance": maintenance,
        "latency_ms": round(latency, 2),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/dashboard")
async def dashboard():
    """Simple HTML dashboard"""
    recent = predictions[-20:] if predictions else []
    high_risk = [p for p in predictions if p["probability"] > ALERT_THRESHOLD][-10:]
    
    return f"""
    <html>
    <head><title>Predictive Maintenance</title>
    <meta http-equiv="refresh" content="10">
    <style>
        body {{font-family: Arial; margin: 20px; background: #1a1a2e; color: white;}}
        .container {{max-width: 800px; margin: auto;}}
        .alert {{background: #e94560; padding: 10px; margin: 5px; border-radius: 5px;}}
        .good {{background: #0f3460; padding: 10px; margin: 5px; border-radius: 5px;}}
        .metric {{display: inline-block; width: 200px; margin: 10px; padding: 15px; background: #16213e; border-radius: 5px;}}
    </style>
    </head>
    <body>
    <div class="container">
        <h1> Predictive Maintenance Dashboard</h1>
        <div>
            <div class="metric">Total Predictions: {len(predictions)}</div>
            <div class="metric">High Risk Alerts: {len(high_risk)}</div>
        </div>
        <h2> Recent High Risk Alerts</h2>
        {''.join([f'<div class="alert">Machine {a["machine"]} - {a["probability"]:.1%} risk at {a["time"][11:19]}</div>' for a in high_risk]) or '<div class="good">No active alerts</div>'}
        <h2> Latest Predictions</h2>
        {''.join([f'<div class="good">Machine {p["machine"]} - {p["risk"]} risk ({p["probability"]:.1%}) - {p["time"][11:19]}</div>' for p in recent[-10:]])}
    </div>
    </body>
    </html>
    """

@app.get("/health")
async def health():
    return {"status": "healthy", "predictions": len(predictions)}

# ==================== RUN ====================
if __name__ == "__main__":
    print(" Predictive Maintenance System")
    print(f" ML Endpoint: {ML_ENDPOINT}")
    print(f" Dashboard: http://localhost:8000/dashboard")
    print(f" API Docs: http://localhost:8000/docs")
    print("\n Test Command:")
    print('curl -X POST http://localhost:8000/predict-failure \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"MachineID":2,"Temperature":85,"Vibration":0.8,"Pressure":120,"Humidity":60,"Hour":14,"Day":18}\'')
    uvicorn.run(app, host="0.0.0.0", port=8000)