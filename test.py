import streamlit as st
import pandas as pd
from io import BytesIO  # Import BytesIO for in-memory buffer handling
# Define the Streamlit application
def main():
      import hmac
        
        
        
        def check_password():
            """Returns `True` if the user had a correct password."""
        
            def login_form():
                """Form with widgets to collect user information"""
                with st.form("Credentials"):
                    st.text_input("Username", key="username")
                    st.text_input("Password", type="password", key="password")
                    st.form_submit_button("Log in", on_click=password_entered)
        
            def password_entered():
                """Checks whether a password entered by the user is correct."""
                if st.session_state["username"] in st.secrets[
                    "passwords"
                ] and hmac.compare_digest(
                    st.session_state["password"],
                    st.secrets.passwords[st.session_state["username"]],
                ):
                    st.session_state["password_correct"] = True
                    del st.session_state["password"]  # Don't store the username or password.
                    del st.session_state["username"]
                else:
                    st.session_state["password_correct"] = False
        
            # Return True if the username + password is validated.
            if st.session_state.get("password_correct", False):
                return True
        
            # Show inputs for username + password.
            login_form()
            if "password_correct" in st.session_state:
                st.error("😕 User not known or password incorrect")
            return False
        
        
        if not check_password():
            st.stop()
        
        # Main Streamlit app starts here
        st.write("Here goes your normal Streamlit app...")
        st.button("Click me")
        if not check_password():
            st.stop()  # Stop execution if the user is not authenticated
            # Main app logic (accessible only after successful login)
            st.write("Welcome to the authenticated section of the app!")
            st.button("Click me")

    
    st.title("Planner Performance Insights")

    # File upload section
    st.header("Upload Excel Files")
    old_file = st.file_uploader("Upload the old data Excel file", type=["xlsx"])
    new_file = st.file_uploader("Upload the new data Excel file", type=["xlsx"])

    if old_file and new_file:
        # Read the uploaded files
        old_data = pd.read_excel(old_file)
        new_data = pd.read_excel(new_file)

        # Required columns
        required_columns = ["Split Man-Days", "Activity Sub Status", "Split MD Date Year-Month Label", "Project Planner","Activity Name","Project Status"]

        # Check if required columns exist
        if not all(col in old_data.columns for col in required_columns):
            st.error(f"The old file is missing one or more required columns: {required_columns}")
            return

        if not all(col in new_data.columns for col in required_columns):
            st.error(f"The new file is missing one or more required columns: {required_columns}")
            return

        # Filter data to include only required columns
        od = old_data[required_columns]
        nw = new_data[required_columns]

        # Creating new column to categorize man-days
        od["Type"] = od["Activity Sub Status"].apply(lambda x: "Secured" if x  == "Customer accepted" else "Unsecured" )
        od["RC_Status"] = od.apply(lambda row: "RC Not available" if row["Activity Name"] == "RC" and row["Project Status"] in ["Quote Revision", "Final PA Review"] else ("RC available" if row["Activity Name"] == "RC" and row["Project Status"] in ["Reviewed","Review In Progress"] else "Not An RC"), axis=1)
        nw["Type"] = nw["Activity Sub Status"].apply(lambda x: "Secured" if x  == "Customer accepted" else "Unsecured" )
        nw["RC_Status"] = od.apply(lambda row: "RC Not available" if row["Activity Name"] == "RC" and row["Project Status"] in ["Quote Revision", "Final PA Review"] else ("RC available" if row["Activity Name"] == "RC" and row["Project Status"] in ["Reviewed","Review In Progress"] else "Not An RC"), axis=1)

        old_res = od.groupby(['Project Planner', 'Split MD Date Year-Month Label', 'Type'])['Split Man-Days'].sum().reset_index()
        old_res.columns = ['Planner', 'Month', 'Type', 'Man-Days']
        old_res_1 = od.groupby(['Project Planner', 'Split MD Date Year-Month Label', 'RC_Status'])['Split Man-Days'].sum().reset_index()
        old_res_1.columns = ['Planner', 'Month', 'RC_Status', 'RC_Man-Days']
        new_res = nw.groupby(['Project Planner', 'Split MD Date Year-Month Label', 'Type'])['Split Man-Days'].sum().reset_index()
        new_res.columns = ['Planner', 'Month', 'Type', 'Man-Days']
        new_res_1 = nw.groupby(['Project Planner', 'Split MD Date Year-Month Label', 'RC_Status'])['Split Man-Days'].sum().reset_index()
        new_res_1.columns = ['Planner', 'Month', 'RC_Status', 'RC_Man-Days']

        comparison_df = pd.merge(
            old_res,
            new_res,
            on=['Planner', 'Month', 'Type'],
            suffixes=('_old', '_new'),
            how='outer'  # Use 'outer' to include missing rows in either file
        )
        comparison_df_1 = pd.merge(
            old_res_1,
            new_res_1,
            on=['Planner', 'Month', 'RC_Status'],
            suffixes=('_old', '_new'),
            how='outer'  # Use 'outer' to include missing rows in either file
        )


        # Calculate the difference in Split Man-Days
        comparison_df['Man-Days_Moved'] = comparison_df['Man-Days_new'] - comparison_df['Man-Days_old']

        # Pivot table to restructure the data
        pivot_df = comparison_df.pivot_table(
            index=['Planner', 'Month'],
            columns='Type',
            values=['Man-Days_old', 'Man-Days_new', 'Man-Days_Moved'], # Fixed: Changed 'Man-Day_Moved' to 'Man-Day_Difference'
            aggfunc='sum',
            fill_value=0  # Fill missing values with 0
        )

        # Flatten multi-level columns
        pivot_df.columns = [f'{col[0]}_{col[1]}' for col in pivot_df.columns]
        pivot_df = pivot_df.reset_index()

        # Use `.get` to handle potential missing columns
        pivot_df['Total_Man-Days_old'] = pivot_df.get('Man-Days_old_Secured', 0) + pivot_df.get('Man-Days_old_Unsecured', 0)
        pivot_df['Total_Man-Days_new'] = pivot_df.get('Man-Days_new_Secured', 0) + pivot_df.get('Man-Days_new_Unsecured', 0)
        pivot_df['Total_Man-Days Moved'] = pivot_df['Total_Man-Days_new'] - pivot_df['Total_Man-Days_old']
        pivot_df['secured vs portfolio(%)']=pivot_df['Man-Days_new_Unsecured']/pivot_df['Total_Man-Days_new']*100
        # Sort by Planner and Month
        pivot_df = pivot_df[['Planner', 'Month',
                             'Total_Man-Days Moved',
                             'Man-Days_Moved_Secured',
                             'Man-Days_Moved_Unsecured',
                             'secured vs portfolio(%)']]
        # Sort by Planner and Month
        pivot_df = pivot_df.sort_values(by=['Planner', 'Month']).reset_index(drop=True)

        comparison_df_1['RC_Man-Day_Moved'] = comparison_df_1['RC_Man-Days_new'] - comparison_df_1['RC_Man-Days_old']



        # Pivot table to restructure the data
        pivot_df_1 = comparison_df_1.pivot_table(
            index=['Planner', 'Month'],
            columns='RC_Status',
            values=['RC_Man-Days_old', 'RC_Man-Days_new', 'RC_Man-Day_Moved'],
            aggfunc='sum',
            fill_value=0  # Fill missing values with 0
        )

        # Flatten multi-level columns
        pivot_df_1.columns = [f'{col[0]}_{col[1]}' for col in pivot_df_1.columns]
        pivot_df_1 = pivot_df_1.reset_index()

        # Sort by Planner and Month using the columns present in pivot_df_1
        # This line was causing the issue, so it's removed and replaced with the line below
        # pivot_df_1 = pivot_df.sort_values(by=['Planner', 'Month']).reset_index(drop=True)
        pivot_df_1 = pivot_df_1.sort_values(by=['Planner', 'Month']).reset_index(drop=True)  # Sorting pivot_df_1

        # Select desired columns from pivot_df_1. Note the changes in column names
        pivot_df_1 = pivot_df_1[['Planner', 'Month',
                              
                              'RC_Man-Day_Moved_RC Not available',
                              'RC_Man-Day_Moved_RC available']]

        # Sort by Planner and Month
        pivot_df_1 = pivot_df_1.sort_values(by=['Planner', 'Month']).reset_index(drop=True)


        # Display results
        st.header("Comparison Results")
        st.subheader("Month-wise Planner Performance Comparison")
        st.dataframe(pivot_df)

        # Convert DataFrame to Excel in-memory buffer
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pivot_df.to_excel(writer, index=False, sheet_name='Comparison Results')
        processed_data = output.getvalue()

        # Allow download of results
        st.download_button(
            label="Download Comparison Results as Excel",
            data=processed_data,
            file_name="comparison_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        # Display results for "RC Specific"
        st.header("RC Specific")
        st.subheader("Month-wise Planner RC Performance")
        st.dataframe(pivot_df_1) # Corrected variable name to pivot_df_1

        # Convert "RC Specific" DataFrame to Excel in-memory buffer
        output_2 = BytesIO()
        with pd.ExcelWriter(output_2, engine='openpyxl') as writer:
            pivot_df_1.to_excel(writer, index=False, sheet_name='RC Performance') # Corrected variable name to pivot_df_1
        processed_data_2 = output_2.getvalue()

        # Allow download of "RC Specific" results
        st.download_button(
            label="Download RC Specific Results as Excel",
            data=processed_data_2,
            file_name="rc_specific_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # streamlit_app.py


      
    

           
if __name__ == "__main__":
    main()
