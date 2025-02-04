import streamlit as st
import pandas as pd
from io import BytesIO
import hmac

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
            st.error("\ud83d\ude15 User not known or password incorrect")
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
            st.error(
                f"The old file is missing one or more required columns: {required_columns}"
            )
            return

        if not all(col in new_data.columns for col in required_columns):
            st.error(
                f"The new file is missing one or more required columns: {required_columns}"
            )
            return

        od = old_data[required_columns]
        nw = new_data[required_columns]

        # Creating new column to categorize man-days
        od["Type"] = od["Activity Sub Status"].apply(
            lambda x: "Secured" if x == "Customer accepted" else "Unsecured"
        )
        od["RC_Status"] = od.apply(
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

        od["RC_Substatus"] = od.apply(
            lambda row: "Secured" if row["RC_Status"] == "RC available" and row["Type"] == "Secured"
            else "Unsecured" if row["RC_Status"] == "RC available" and row["Type"] == "Unsecured"
            else "NA",
            axis=1
        )
        
        nw["Type"] = nw["Activity Sub Status"].apply(
            lambda x: "Secured" if x == "Customer accepted" else "Unsecured"
        )
        nw["RC_Status"] = nw.apply(
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

        nw["RC_Substatus"] = nw.apply(
            lambda row: "Secured" if row["RC_Status"] == "RC available" and row["Type"] == "Secured" 
            else "Unsecured" if row["RC_Status"] == "RC available" and row["Type"] == "Unsecured" 
            else "NA",
            axis=1
        )
        

        # Aggregating results
        old_res = od.groupby(["Project Planner", "Split MD Date Year-Month Label", "Type"])["Split Man-Days"].sum().reset_index()
        old_res.columns = ["Planner", "Month", "Type", "Man-Days"]
        old_res_1 = od.groupby(['Project Planner', 'Split MD Date Year-Month Label', 'RC_Status','RC_Substatus'])['Split Man-Days'].sum().reset_index()
        old_res_1.columns = ['Planner', 'Month', 'RC_Status','RC_Substatus', 'RC_Man-Days']
        new_res = nw.groupby(["Project Planner", "Split MD Date Year-Month Label", "Type"])["Split Man-Days"].sum().reset_index()
        new_res.columns = ["Planner", "Month", "Type", "Man-Days"]
        new_res_1 = nw.groupby(['Project Planner', 'Split MD Date Year-Month Label', 'RC_Status','RC_Substatus'])['Split Man-Days'].sum().reset_index()
        new_res_1.columns = ['Planner', 'Month', 'RC_Status','RC_Substatus', 'RC_Man-Days']

        # Merging results
        comparison_df = pd.merge(
            old_res,
            new_res,
            on=["Planner", "Month", "Type"],
            suffixes=("_old", "_new"),
            how="outer",
        )
        comparison_df_1 = pd.merge(
            old_res_1,
            new_res_1,
            on=["Planner", "Month", "RC_Status", "RC_Substatus"],
            suffixes=("_old", "_new"),
            how="outer",
        ).fillna(0) 

        # Calculating differences
        comparison_df["Man-Days_Diff"] = (
            comparison_df["Man-Days_new"] - comparison_df["Man-Days_old"]
        )
        comparison_df_1["RC_Man-Days_Diff"] = (
            comparison_df_1["RC_Man-Days_new"] - comparison_df_1["RC_Man-Days_old"]
        )

        # Creating pivot tables
        pivot_df = comparison_df.pivot_table(
            index=["Planner", "Month"],
            columns="Type",
            values=["Man-Days_old", "Man-Days_new", "Man-Days_Diff"],
            aggfunc="sum",
            fill_value=0,
        ).reset_index()

        pivot_df_1 = comparison_df_1.pivot_table(
            index=['Planner', 'Month'],
            columns=['RC_Status','RC_Substatus'],  
            values=['RC_Man-Days_old', 'RC_Man-Days_new', 'RC_Man-Days_Diff'],  
            aggfunc='sum',  
            fill_value=0  
        ).reset_index()

        # Flattening column names
        pivot_df.columns = ["_".join(col).strip("_") for col in pivot_df.columns]
        pivot_df_1.columns = [f'{col[0]}_{col[1]}_{col[2]}' for col in pivot_df_1.columns]

        # Adding additional columns
        pivot_df["Total_portfolio_old"] = pivot_df.get("Man-Days_old_Secured", 0) + pivot_df.get("Man-Days_old_Unsecured", 0)
        pivot_df["Total_portfolio_new"] = pivot_df.get("Man-Days_new_Secured", 0) + pivot_df.get("Man-Days_new_Unsecured", 0)
        pivot_df["Total_portfolio Diff"] = pivot_df["Total_portfolio_new"] - pivot_df["Total_portfolio_old"]
        pivot_df["secured vs portfolio(%)"] = (
            pivot_df.get("Man-Days_new_Secured", 0) / pivot_df["Total_portfolio_new"] * 100
        )
        
        pivot_df_1["RC_Total_portfolio_old"] = pivot_df_1.get("RC_Man-Days_old_RC available_Secured", 0) + pivot_df_1.get("RC_Man-Days_old_RC available_Unsecured", 0) + pivot_df_1.get("RC_Man-Days_old_RC Not available_NA",0)
        pivot_df_1["RC_Total_portfolio_new"] = pivot_df_1.get("RC_Man-Days_new_RC available_Secured", 0) + pivot_df_1.get("RC_Man-Days_new_RC available_Unsecured", 0) + pivot_df_1.get("RC_Man-Days_new_RC Not available_NA",0)
        pivot_df_1["RC_Available_portfolio_new"] = pivot_df_1.get("RC_Man-Days_new_RC available_Secured", 0) + pivot_df_1.get("RC_Man-Days_new_RC available_Unsecured", 0)
        pivot_df_1["RC_Available_portfolio_old"] = pivot_df_1.get("RC_Man-Days_old_RC available_Secured", 0) + pivot_df_1.get("RC_Man-Days_old_RC available_Unsecured", 0) 
        
        pivot_df_1["RC_Total_portfolio Diff"] = pivot_df_1["RC_Total_portfolio_new"] - pivot_df_1["RC_Total_portfolio_old"]
        pivot_df_1["RC_Available_portfolio Diff"] = pivot_df_1["RC_Available_portfolio_new"] - pivot_df_1["RC_Available_portfolio_old"]

        # Sorting and selecting columns
        pivot_df = pivot_df[[
            "Planner", "Month",
            "Total_portfolio Diff",
            "Man-Days_Diff_Secured",
            "Man-Days_Diff_Unsecured",
            "secured vs portfolio(%)",
        ]].sort_values(by=["Planner", "Month"]).reset_index(drop=True)


        pivot_df_1 = pivot_df_1[[
            "Planner__", "Month__",
            "RC_Total_portfolio_new",
            "RC_Man-Days_new_RC available_Secured",
            "RC_Man-Days_new_RC available_Unsecured",
            "RC_Available_portfolio_new",
            "RC_Total_portfolio Diff",
            "RC_Man-Days_Diff_RC available_Secured",
            "RC_Man-Days_Diff_RC available_Unsecured",
            "RC_Available_portfolio Diff",

        ]].sort_values(by=["Planner__", "Month__"]).reset_index(drop=True)

        # Output to Streamlit
        st.header("Comparison Results")
        st.dataframe(pivot_df)
        st.dataframe(pivot_df_1)

        # Optional: Save and download results as Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            pivot_df.to_excel(writer, index=False, sheet_name="Comparison Results")
            pivot_df_1.to_excel(writer, index=False, sheet_name="RC Comparison Results")
        st.download_button(
            label="Download Results",
            data=output.getvalue(),
            file_name="comparison_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

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
                    update_excel_results(temp_path, pivot_df)

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

def update_excel_results(file_path, data, sheet_name="Comparison Results"):
    """Updates the given Excel file with new data while keeping existing charts intact."""
    book = load_workbook(file_path)  # Load existing Excel file
    
    with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        writer.book = book
        data.to_excel(writer, sheet_name=sheet_name, index=False)
        writer.close()

if __name__ == "__main__":
    main()














