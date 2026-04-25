from fastapi import FastAPI
import pickle

app = FastAPI()

model = pickle.load(
open("failure_model 2nd Project.pkl","rb")
)

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

    data=[[
    machine_id,
    temperature,
    vibration,
    pressure,
    humidity,
    hour,
    day
    ]]

    prediction=model.predict(data)[0]

    probability=model.predict_proba(
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