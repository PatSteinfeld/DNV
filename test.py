import streamlit as st
import pandas as pd
from io import BytesIO
import hmac
from openpyxl import load_workbook

def main():
    def check_password():
        """Returns `True` if the user had a correct password."""
        def login_form():
            with st.form("Credentials"):
                st.text_input("Username", key="username")
                st.text_input("Password", type="password", key="password")
                st.form_submit_button("Log in", on_click=password_entered)

        def password_entered():
            if (
                st.session_state["username"] in st.secrets["passwords"]
                and hmac.compare_digest(
                    st.session_state["password"],
                    st.secrets.passwords[st.session_state["username"]],
                )
            ):
                st.session_state["password_correct"] = True
                del st.session_state["password"]
                del st.session_state["username"]
            else:
                st.session_state["password_correct"] = False

        if st.session_state.get("password_correct", False):
            return True

        login_form()
        if "password_correct" in st.session_state:
            st.error("😕 User not known or password incorrect")
        return False

    if not check_password():
        st.stop()

    st.title("Planner Performance Insights")

    st.header("Upload Excel Files")
    old_file = st.file_uploader("Upload the old data Excel file", type=["xlsx"])
    new_file = st.file_uploader("Upload the new data Excel file", type=["xlsx"])

    if old_file and new_file:
        old_data = pd.read_excel(old_file)
        new_data = pd.read_excel(new_file)

        required_columns = [
            "Split Man-Days",
            "Activity Sub Status",
            "Split MD Date Year-Month Label",
            "Project Planner",
            "Activity Name",
            "Project Status",
        ]

        if not all(col in old_data.columns for col in required_columns):
            st.error("The old file is missing one or more required columns.")
            return

        if not all(col in new_data.columns for col in required_columns):
            st.error("The new file is missing one or more required columns.")
            return

        # Processing old and new data
        for df in [old_data, new_data]:
            df["Type"] = df["Activity Sub Status"].apply(
                lambda x: "Secured" if x == "Customer accepted" else "Unsecured"
            )
            df["RC_Status"] = df.apply(
                lambda row: "RC Not available"
                if row["Activity Name"] == "RC"
                and row["Project Status"] in ["Quote Revision", "Final PA Review"]
                else (
                    "RC available"
                    if row["Activity Name"] == "RC"
                    and row["Project Status"] in ["Reviewed", "Review In Progress"]
                    else "Not An RC"
                ),
                axis=1,
            )
            df["RC_Substatus"] = df.apply(
                lambda row: "Secured" if row["RC_Status"] == "RC available" and row["Type"] == "Secured"
                else "Unsecured" if row["RC_Status"] == "RC available" and row["Type"] == "Unsecured"
                else "NA",
                axis=1,
            )

        # Aggregating results
        old_res = old_data.groupby(["Project Planner", "Split MD Date Year-Month Label", "Type"])["Split Man-Days"].sum().reset_index()
        old_res.columns = ["Planner", "Month", "Type", "Man-Days"]

        old_res_1 = old_data.groupby(['Project Planner', 'Split MD Date Year-Month Label', 'RC_Status','RC_Substatus'])['Split Man-Days'].sum().reset_index()
        old_res_1.columns = ['Planner', 'Month', 'RC_Status','RC_Substatus', 'RC_Man-Days']

        new_res = new_data.groupby(["Project Planner", "Split MD Date Year-Month Label", "Type"])["Split Man-Days"].sum().reset_index()
        new_res.columns = ["Planner", "Month", "Type", "Man-Days"]

        new_res_1 = new_data.groupby(['Project Planner', 'Split MD Date Year-Month Label', 'RC_Status','RC_Substatus'])['Split Man-Days'].sum().reset_index()
        new_res_1.columns = ['Planner', 'Month', 'RC_Status','RC_Substatus', 'RC_Man-Days']

        # Merging results
        comparison_df = pd.merge(
            old_res, new_res, on=["Planner", "Month", "Type"], suffixes=("_old", "_new"), how="outer"
        ).fillna(0)

        comparison_df_1 = pd.merge(
            old_res_1, new_res_1, on=["Planner", "Month", "RC_Status", "RC_Substatus"], suffixes=("_old", "_new"), how="outer"
        ).fillna(0)

        # Calculating differences
        comparison_df["Man-Days_Diff"] = comparison_df["Man-Days_new"] - comparison_df["Man-Days_old"]
        comparison_df_1["RC_Man-Days_Diff"] = comparison_df_1["RC_Man-Days_new"] - comparison_df_1["RC_Man-Days_old"]

        # Output to Streamlit
        st.header("Comparison Results")
        st.dataframe(comparison_df)
        st.dataframe(comparison_df_1)

        # Upload button for selecting the Excel file with charts to update
        st.header("Upload the Excel File with Charts to Update")
        excel_file = st.file_uploader("Upload the Excel file with charts", type=["xlsx"])

        if excel_file:
            if st.button("Update Excel File with Charts"):
                try:
                    # Save uploaded file temporarily
                    temp_path = "temp_updated_excel.xlsx"
                    with open(temp_path, "wb") as f:
                        f.write(excel_file.getbuffer())

                    # Update the Excel file
                    update_excel_results(temp_path, comparison_df, comparison_df_1)

                    # Provide updated file for download
                    with open(temp_path, "rb") as f:
                        st.download_button(
                            label="Download Updated Excel File",
                            data=f,
                            file_name="Updated_Performance_Report.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                    st.success("Excel file updated successfully! Charts will reflect new data.")

                except Exception as e:
                    st.error(f"Error updating Excel file: {e}")

def update_excel_results(file_path, data1, data2):
    """Updates the given Excel file with new data while keeping existing charts intact."""
    book = load_workbook(file_path)  # Load existing Excel file

    with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        writer._book = book  # Assign workbook correctly
        data1.to_excel(writer, sheet_name="Comparison Results", index=False)
        data2.to_excel(writer, sheet_name="RC Specefic", index=False)
        writer._save()  # Explicitly save changes


if __name__ == "__main__":
    main()














