from datetime import datetime, date
import json
import logging
import re
from openai import AzureOpenAI
from sqlalchemy import text
from .config import AZURE_API_KEY, AZURE_ENDPOINT, AZURE_API_VERSION, AZURE_MODEL
from .db import get_engine

logger = logging.getLogger(__name__)

client = AzureOpenAI(
    api_key     = AZURE_API_KEY,
    azure_endpoint = AZURE_ENDPOINT,
    api_version = AZURE_API_VERSION
)

'''def few_shot_prediction(details: str):
    prompt = f"""
    Observe the employee data provided ...
    Employee data: {details}
    """
    messages = [
        {"role": "system", "content": "You are a helpful assistant ..."},
        {"role": "user",   "content": prompt}
    ]
    resp = client.chat.completions.create(
        model       = AZURE_MODEL,
        messages    = messages,
        max_tokens  = 700,
        temperature = 0.1
    )
    content = resp.choices[0].message.content

    # parse content for percentage, label, summary, analysis...
    # (same parsing logic as before)
    # return percentage, label, summary, analysis, color'''

def few_shot_prediction(employee_data):
    # Few-shot examples for churn prediction
    few_shot_prompt = """
    Observe the employee data provided and identify relationships between variables like a machine learning algorithm. 
    Predict the likelihood of churn for the employee as a percentage between 0 and 100.

    Return only a valid JSON object, with no Markdown or text outside the object:
    {{
      "likelihood": <number from 0 to 100>,
      "ai_confidence": <integer from 1 to 100>,
      "summary": "<brief explanation>",
      "feature_analysis": "<key factors and their relationship to churn>"
    }}

    AI confidence measures confidence in the prediction, not likelihood of churn.
    Reduce it substantially when fields are marked "Not provided" or listed as missing,
    especially for performance, potential, salary, tenure, or work-pattern data.
      
    Employee data: {employee_data}
    """.format(employee_data=employee_data)

    # OpenAI API chat message structure
    messages = [
        {"role": "system", "content": "You are a helpful assistant that simulates the behavior of a machine learning model."},
        {"role": "user", "content": few_shot_prompt}
    ]

    # Call to OpenAI Chat Completions API
    response = client.chat.completions.create(
        model=AZURE_MODEL,
        messages=messages,
        max_tokens=700,
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    # Extract the content from the response
    content = response.choices[0].message.content.strip()

    prediction_percentage = 0.0
    ai_confidence = 1
    summary = "The model did not provide a summary."
    feature_analysis = "The model did not provide feature analysis."

    try:
        prediction = json.loads(content)
        prediction_percentage = max(0.0, min(100.0, float(prediction["likelihood"])))
        ai_confidence = max(1, min(100, int(round(float(prediction["ai_confidence"])))))
        summary = str(prediction["summary"]).strip() or summary
        feature_analysis = str(prediction["feature_analysis"]).strip() or feature_analysis
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        # Preserve useful results from older/plain-text deployments instead of
        # replacing every response field with N/A when a single parse fails.
        logger.warning("Prediction response was not valid JSON; using text fallback: %s", error)
        likelihood_match = re.search(
            r"Likelihood\s+of\s+Churn[^0-9]{0,20}(\d+(?:\.\d+)?)\s*%?",
            content,
            re.IGNORECASE,
        )
        confidence_match = re.search(r"AI\s+Confidence[^0-9]{0,20}(\d{1,3})", content, re.IGNORECASE)
        summary_match = re.search(
            r"Summary\s*:\s*(.*?)(?=Key\s+Features\s+Analysis\s*:|$)",
            content,
            re.IGNORECASE | re.DOTALL,
        )
        analysis_match = re.search(r"Key\s+Features\s+Analysis\s*:\s*(.*)", content, re.IGNORECASE | re.DOTALL)

        if likelihood_match:
            prediction_percentage = max(0.0, min(100.0, float(likelihood_match.group(1))))
        if confidence_match:
            ai_confidence = max(1, min(100, int(confidence_match.group(1))))
        if summary_match and summary_match.group(1).strip():
            summary = summary_match.group(1).strip()
        if analysis_match and analysis_match.group(1).strip():
            feature_analysis = analysis_match.group(1).strip()

    if prediction_percentage < 25:
        prediction_label = "Not likely to churn"
    elif prediction_percentage <= 50:
        prediction_label = "Less likely to churn"
    elif prediction_percentage <= 75:
        prediction_label = "Likely to churn"
    else:
        prediction_label = "Very likely to churn"

    return prediction_percentage, prediction_label, summary, feature_analysis, ai_confidence

def update_or_insert_prediction(employee_id: int, data: dict):
    engine = get_engine()
    check_q = "SELECT COUNT(*) FROM employees_churn_predictions WHERE employeeId=:eid"
    with engine.begin() as conn:
        cnt = conn.execute(text(check_q), {"eid": employee_id}).scalar()
        if cnt:
            upd = text("""
                UPDATE employees_churn_predictions SET
                    predictionPercentage=:prediction_percentage,
                    predictionLabel=:prediction_label,
                    summary=:summary,
                    featureAnalysis=:feature_analysis,
                    color=:color,
                    predictionDate=:date,
                    companyId=:companyId,
                    updatedAt=:updatedAt
                WHERE employeeId=:employee_id
            """)
            conn.execute(upd, data)
        else:
            ins = text("""
                INSERT INTO employees_churn_predictions
                (employeeId,predictionPercentage,predictionLabel,summary,featureAnalysis,
                 color,predictionDate,companyId,createdAt,updatedAt)
                VALUES
                (:employee_id,:prediction_percentage,:prediction_label,:summary,
                 :feature_analysis,:color,:date,:companyId,:createdAt,:updatedAt)
            """)
            conn.execute(ins, data)
