import uvicorn
from fastapi import FastAPI, HTTPException
from .data_processing import get_view_as_dataframe, process_dataframe, transform_dataframe
from .prediction import few_shot_prediction, update_or_insert_prediction
from .db import get_engine
from datetime import datetime, date

app = FastAPI(title="Churn Prediction API")

@app.get("/")
def health_check():
    return {"status": "API is running"}

@app.post("/predict/{employee_id}")
async def predict_churn(employee_id: int):
    df = get_view_as_dataframe("EmployeeDetails_view", employee_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    proc = process_dataframe(df)
    if proc is None:
        raise HTTPException(status_code=400, detail="Missing required data")
    trans = transform_dataframe(proc)
    details = trans["details"].iloc[0]
    pct, label, summary, analysis, color = few_shot_prediction(details)

    data = {
        "employee_id": employee_id,
        "prediction_percentage": pct,
        "prediction_label": label,
        "summary": summary,
        "feature_analysis": analysis,
        "color": color,
        "date": datetime.now(),
        "companyId": proc["Company_ID"].iloc[0],
        "createdAt": date.today(),
        "updatedAt": date.today(),
    }
    update_or_insert_prediction(employee_id, data)
    return {"employee_id": employee_id, "likelihood": pct, "category": label}

def run_app():
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    run_app()
