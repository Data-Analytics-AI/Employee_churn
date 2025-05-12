from .data_processing import get_entire_view_as_dataframe
from .main import process_employee

def process_all_employees():
    df = get_entire_view_as_dataframe("EmployeeDetails_view")
    if df is None or df.empty:
        print("No employees found.")
        return

    for eid in df["Employee ID"]:
        try:
            print(f"Processing {eid}…")
            process_employee(eid)
        except Exception as e:
            print(f"Failed {eid}: {e}")
