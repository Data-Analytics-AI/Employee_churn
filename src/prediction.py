from datetime import datetime, date
from openai import AzureOpenAI
from sqlalchemy import text
from .config import AZURE_API_KEY, AZURE_ENDPOINT, AZURE_API_VERSION, AZURE_MODEL
from .db import get_engine

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
    Predict the likelihood of churn for the employee as a percentage titled "Likelihood of Churn:" (between 0% and 100%)
    
    Additionally, provide:
    - A categorization (titled "Category:") categorized as:
        - "Not likely to churn" (if prediction is less than 25%),
        - "Less likely to churn" (if prediction is 25%-50%),
        - "Likely to churn" (if prediction is 50%-75%),
        - "Very likely to churn" (if prediction is above 75%).
    - A brief summary (titled "Summary:") explaining the prediction.
    - An analysis of key features (titled "Key Features Analysis:") in the format:
      "feature: positive relationship (or negative relationship): reason".
      
    Employee data: {employee_data}
    """.format(employee_data=employee_data)

    # OpenAI API chat message structure
    messages = [
        {"role": "system", "content": "You are a helpful assistant that simulates the behavior of a machine learning model."},
        {"role": "user", "content": few_shot_prompt}
    ]

    # Call to OpenAI Chat Completions API
    response = client.chat.completions.create(
        model="gpt-4o",  # -new Ensure this matches your model deployment
        messages=messages,
        max_tokens=700,
        temperature=0.1
    )
    print(response)

    # Extract the content from the response
    content = response.choices[0].message.content.strip()
    #print(content)

    # Initialize default return values
    prediction_percentage = 0
    prediction_label = "Prediction not available"
    summary = "Summary not found in response."
    feature_analysis = "Feature analysis not found in response."

    # Parse the response to extract the churn prediction percentage, summary, and feature analysis
    try:
        # Extract the prediction percentage
        percentage_start = content.find("Likelihood of Churn:")
        percentage_end = content.find("%", percentage_start)
        if percentage_start != -1 and percentage_end != -1:
            prediction_percentage = float(content[percentage_start + len("Likelihood of Churn:"):percentage_end].strip())

        # Determine the prediction label based on the prediction percentage
        if prediction_percentage < 25:
            prediction_label = "Not likely to churn"
            color = "green"
        elif 25 <= prediction_percentage <= 50:
            prediction_label = "Less likely to churn"
            color = "lightgreen"
        elif 50 < prediction_percentage <= 75:
            prediction_label = "Likely to churn"
            color = "yellow"
        else:
            prediction_label = "Very likely to churn"
            color = "red"

        # Extract the summary
        summary_start = content.find("Summary:")
        analysis_start = content.find("Key Features Analysis:")
        if summary_start != -1 and analysis_start != -1:
            summary = content[summary_start + len("Summary:"):analysis_start].strip()

        # Extract the feature analysis
        analysis_start = content.find("Key Features Analysis:")
        if analysis_start != -1:
            feature_analysis = content[analysis_start + len("Key Features Analysis:"):].strip()

    except Exception as e:
        # Handle any parsing errors
        prediction_percentage = "N/A"#Prediction percentage parsing error"
        prediction_label = "N/A"#Prediction label parsing error"
        summary = "N/A"#Summary parsing error"
        feature_analysis = "N/A"#Feature analysis parsing error"
        color = "N/A"

    return prediction_percentage, prediction_label, summary, feature_analysis, color

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
