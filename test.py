import streamlit as st
import pandas as pd
from io import BytesIO
import hmac

def main():
    def check_password():
        """Validate the user credentials."""

        def login_form():
            with st.form("Login Form"):
                st.text_input("Username", key="username")
                st.text_input("Password", type="password", key="password")
                st.form_submit_button("Log In", on_click=validate_credentials)

        def validate_credentials():
            if (
                st.session_state.get("username") in st.secrets["passwords"]
                and hmac.compare_digest(
                    st.session_state.get("password"),
                    st.secrets.passwords[st.session_state["username"]],
                )
            ):
                st.session_state["authenticated"] = True
                st.session_state.pop("password", None)
                st.session_state.pop("username", None)
            else:
                st.session_state["authenticated"] = False

        if st.session_state.get("authenticated", False):
            return True

        login_form()

        if "authenticated" in st.session_state and not st.session_state["authenticated"]:
            st.error("Invalid username or password.")

        return False

    if not check_password():
        st.stop()

    st.title("Planner Performance Insights")

    st.header("Upload Excel Files")
    old_file = st.file_uploader("Upload the old data Excel file", type="xlsx")
    new_file = st.file_uploader("Upload the new data Excel file", type="xlsx")

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

        for file_name, data in zip(["Old", "New"], [old_data, new_data]):
            if not all(col in data.columns for col in required_columns):
                st.error(f"The {file_name} file is missing one or more required columns: {required_columns}")
                return

        def process_data(data):
            data = data[required_columns].copy()
            data["Type"] = data["Activity Sub Status"].apply(
                lambda x: "Secured" if x == "Customer accepted" else "Unsecured"
            )
            data["RC_Status"] = data.apply(
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
            return data

        old_data = process_data(old_data)
        new_data = process_data(new_data)

        def aggregate_data(data, group_cols, value_col, suffix):
            aggregated = data.groupby(group_cols)[value_col].sum().reset_index()
            aggregated.columns = group_cols + [f"{value_col}_{suffix}"]
            return aggregated

        old_agg = aggregate_data(
            old_data, ["Project Planner", "Split MD Date Year-Month Label", "Type"], "Split Man-Days", "old"
        )
        new_agg = aggregate_data(
            new_data, ["Project Planner", "Split MD Date Year-Month Label", "Type"], "Split Man-Days", "new"
        )

        comparison_df = pd.merge(
            old_agg,
            new_agg,
            on=["Project Planner", "Split MD Date Year-Month Label", "Type"],
            how="outer",
        )
        comparison_df["Man-Days_Diff"] = (
            comparison_df["Split Man-Days_new"] - comparison_df["Split Man-Days_old"]
        )

        pivot_df = comparison_df.pivot_table(
            index=["Project Planner", "Split MD Date Year-Month Label"],
            columns="Type",
            values=["Split Man-Days_old", "Split Man-Days_new", "Man-Days_Diff"],
            aggfunc="sum",
            fill_value=0,
        )
        pivot_df.columns = [f"{col[0]}_{col[1]}" for col in pivot_df.columns]
        pivot_df.reset_index(inplace=True)

        pivot_df["Total_Man-Days_old"] = pivot_df.filter(like="Split Man-Days_old").sum(axis=1)
        pivot_df["Total_Man-Days_new"] = pivot_df.filter(like="Split Man-Days_new").sum(axis=1)
        pivot_df["Total_Man-Days_Diff"] = pivot_df["Total_Man-Days_new"] - pivot_df["Total_Man-Days_old"]
        pivot_df["Secured_vs_Portfolio_%"] = (
            pivot_df.get("Split Man-Days_new_Unsecured", 0)
            / pivot_df["Total_Man-Days_new"]
            * 100
        ).fillna(0)

        pivot_df = pivot_df[
            [
                "Project Planner",
                "Split MD Date Year-Month Label",
                "Total_Man-Days_Diff",
                "Split Man-Days_Diff_Secured",
                "Split Man-Days_Diff_Unsecured",
                "Secured_vs_Portfolio_%",
            ]
        ].sort_values(by=["Project Planner", "Split MD Date Year-Month Label"])

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            pivot_df.to_excel(writer, index=False, sheet_name="Comparison Results")

        st.header("Comparison Results")
        st.dataframe(pivot_df)

        st.download_button(
            "Download Results as Excel",
            data=output.getvalue(),
            file_name="comparison_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

if __name__ == "__main__":
    main()





