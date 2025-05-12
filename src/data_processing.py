import pandas as pd
from datetime import datetime
from sqlalchemy import text
from .db import get_engine

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
    df["full_name"] = df["First Name"] + " " + df["Last Name"]
    now = datetime.now().year
    df["Age"] = now - pd.to_datetime(df["Date Of Birth"]).dt.year
    df["tenure_at_company"] = now - pd.to_datetime(df["Hire Date"]).dt.year
    df["tenure_at_company"] = df["tenure_at_company"].apply(lambda x: "<1" if x < 1 else x)

    required = [
        "Gender","Marital Status","Department","Designation","Grade",
        "Employment Type","Work Model","Number Of Days Per Week",
        "Leave Length","Payroll Type","Monthly Gross","Salary Frequency",
        "Age","tenure_at_company"
    ]
    if df[required].isnull().any().any():
        return None
    return df

def transform_dataframe(df: pd.DataFrame) -> pd.DataFrame | None:
    df = df.copy()
    df["details"] = df.apply(lambda r: (
        f"Gender: {r['Gender']}, Marital Status: {r['Marital Status']}, Department: {r['Department']}, "
        f"Designation: {r['Designation']}, Grade: {r['Grade']}, Employment Type: {r['Employment Type']}, "
        f"Work Model: {r['Work Model']}, Number of Days Per Week: {r['Number Of Days Per Week']}, "
        f"Leave Length: {r['Leave Length']}, Payroll Type: {r['Payroll Type']}, "
        f"Monthly Gross: {r['Monthly Gross']} Naira, Salary Frequency: {r['Salary Frequency']}, "
        f"Age: {r['Age']}, tenure_at_company: {r['tenure_at_company']}"
    ), axis=1)
    return df[["Employee ID", "full_name", "Work Status", "details"]]
