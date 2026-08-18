import pandas as pd
from datetime import datetime
from sqlalchemy import text
from .db import get_engine

PREDICTION_FIELDS = [
    "Gender", "Marital Status", "Department", "Designation", "Grade",
    "Employment Type", "Work Model", "Number Of Days Per Week",
    "Leave Length", "Payroll Type", "Monthly Gross", "Salary Frequency",
    "Age", "tenure_at_company", "Performance Score", "Potential Score",
]

def is_missing(value) -> bool:
    """Return whether a scalar database value is unavailable for prediction."""
    return pd.isna(value) or (isinstance(value, str) and not value.strip())

'''def get_view_as_dataframe(view_name: str, employee_id: int) -> pd.DataFrame | None:
    query = f"SELECT * FROM {view_name} WHERE `Employee ID` = :eid"
    df = pd.read_sql(query, con=get_engine(), params={"eid": employee_id})
    return df if not df.empty else None'''

def get_view_as_dataframe(view_name: str, employee_id: int) -> pd.DataFrame | None:
    """
    Fetch a single row from the database view by Employee ID.
    """
    query = text(f"SELECT * FROM {view_name} WHERE `Employee ID` = :eid")
    try:
        df = pd.read_sql(query, con=get_engine(), params={"eid": employee_id})
        return df if not df.empty else None
    except Exception as e:
        print(f"An error occurred while fetching the data: {e}")
        return None

def get_entire_view_as_dataframe(view_name: str) -> pd.DataFrame | None:
    query = f"SELECT * FROM {view_name}"
    return pd.read_sql(query, con=get_engine())

def process_dataframe(df: pd.DataFrame) -> pd.DataFrame | None:
    df = df.copy()
    # Missing fields should be visible to the prediction model rather than causing
    # the whole prediction to be rejected.
    for column in ["First Name", "Last Name", "Date Of Birth", "Hire Date", *PREDICTION_FIELDS]:
        if column not in df.columns:
            df[column] = pd.NA

    df["full_name"] = (
        df["First Name"].fillna("").astype(str).str.strip() + " " +
        df["Last Name"].fillna("").astype(str).str.strip()
    ).str.strip().replace("", "Unknown employee")
    now = datetime.now().year
    df["Age"] = now - pd.to_datetime(df["Date Of Birth"], errors="coerce").dt.year
    df["tenure_at_company"] = now - pd.to_datetime(df["Hire Date"], errors="coerce").dt.year
    df["tenure_at_company"] = df["tenure_at_company"].apply(
        lambda x: "<1" if pd.notna(x) and x < 1 else x
    )

    df["missing_prediction_fields"] = df[PREDICTION_FIELDS].apply(
        lambda row: ", ".join(column for column, value in row.items() if is_missing(value)),
        axis=1,
    )
    return df

def transform_dataframe(df: pd.DataFrame) -> pd.DataFrame | None:
    df = df.copy()
    def display_value(value):
        return "Not provided" if is_missing(value) else value

    df["details"] = df.apply(lambda r: (
        f"Gender: {display_value(r['Gender'])}, Marital Status: {display_value(r['Marital Status'])}, Department: {display_value(r['Department'])}, "
        f"Designation: {display_value(r['Designation'])}, Grade: {display_value(r['Grade'])}, Employment Type: {display_value(r['Employment Type'])}, "
        f"Work Model: {display_value(r['Work Model'])}, Number of Days Per Week: {display_value(r['Number Of Days Per Week'])}, "
        f"Leave Length: {display_value(r['Leave Length'])}, Payroll Type: {display_value(r['Payroll Type'])}, "
        f"Monthly Gross: {display_value(r['Monthly Gross'])} Naira, Salary Frequency: {display_value(r['Salary Frequency'])}, "
        f"Age: {display_value(r['Age'])}, tenure_at_company: {display_value(r['tenure_at_company'])}, "
        f"Performance Score: {display_value(r['Performance Score'])}, Potential Score: {display_value(r['Potential Score'])}. "
        f"Missing fields: {r['missing_prediction_fields'] or 'None'}"
    ), axis=1)
    return df[["Employee ID", "full_name", "Work Status", "details"]]
