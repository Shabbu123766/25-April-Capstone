from fastapi import FastAPI
import pickle

app=FastAPI()

model=pickle.load(
open("model.pkl","rb")
)

@app.get("/")
def home():
    return {"message":"API Working"}

@app.post("/predict-demand")
def predict(
product_id:int,
category:int,
region:int,
price:float,
discount:float,
holiday:int
):

    data=[[
    product_id,
    category,
    region,
    price,
    discount,
    holiday
    ]]

    prediction=model.predict(data)

    return {
      "Predicted Demand":
      float(prediction[0])
    }