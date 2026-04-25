from fastapi import FastAPI
import pickle
import pandas as pd

app = FastAPI()

# Load trained model
model = pickle.load(
open("failure_model.pkl","rb")
)


@app.get("/")
def home():
    return {
        "message":"Predictive Maintenance API Running"
    }


@app.post("/predict-failure")
def predict_failure(
machine_id:int,
temperature:float,
vibration:float,
pressure:float,
humidity:float,
hour:int,
day:int
):

    # Input data
    data = pd.DataFrame([{
        "MachineID": machine_id,
        "Temperature": temperature,
        "Vibration": vibration,
        "Pressure": pressure,
        "Humidity": humidity,
        "Hour": hour,
        "Day": day
    }])

    # Prediction
    prediction = model.predict(data)[0]

    probability = model.predict_proba(
        data
    )[0][1]


    # Alert Logic
    alert="Normal"

    if probability > 0.8:
        alert="Maintenance Alert Triggered"


    return {
        "Failure Prediction": int(prediction),
        "Failure Probability": float(probability),
        "Alert": alert
    }