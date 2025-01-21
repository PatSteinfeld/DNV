import streamlit as st
import pandas as pd
from io import BytesIO  # Import BytesIO for in-memory buffer handling
# Define the Streamlit application
def main():
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
        required_columns = ["Split Man-Days", "Activity Sub Status", "Split MD Date Year-Month Label", "Project Planner"]

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

        nw["Type"] = nw["Activity Sub Status"].apply(lambda x: "Secured" if x  == "Customer accepted" else "Unsecured" )


        old_res = od.groupby(['Project Planner', 'Split MD Date Year-Month Label', 'Type'])['Split Man-Days'].sum().reset_index()
        old_res.columns = ['Planner', 'Month', 'Type', 'Man-Days']
        new_res = nw.groupby(['Project Planner', 'Split MD Date Year-Month Label', 'Type'])['Split Man-Days'].sum().reset_index()
        new_res.columns = ['Planner', 'Month', 'Type', 'Man-Days']

        comparison_df = pd.merge(
        old_res,
        new_res,
        on=['Planner', 'Month', 'Type'],
        suffixes=('_old', '_new'),
        how='outer'  # Use 'outer' to include missing rows in either file
        )


        # Calculate the difference in Split Man-Days
        comparison_df['Man-Day_Moved'] = comparison_df['Man-Days_new'] - comparison_df['Man-Days_old']

        # Pivot table to restructure the data
        pivot_df = comparison_df.pivot_table(
            index=['Planner', 'Month'],
            columns='Type',
            values=['Man-Days_old', 'Man-Days_new', 'Man-Day_Moved'], # Fixed: Changed 'Man-Day_Moved' to 'Man-Day_Difference'
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

        # Sort by Planner and Month
        pivot_df = pivot_df.sort_values(by=['Planner', 'Month']).reset_index(drop=True)
        pivot_df = pivot_df[['Planner', 'Month',
                             'Total_Man-Days_old', 'Total_Man-Days_new', 'Total_Man-Days Moved',
                             'Man-Days_old_Secured', 'Man-Days_new_Secured', 'Man-Day_Moved_Secured',
                             'Man-Days_old_Unsecured', 'Man-Days_new_Unsecured', 'Man-Day_Moved_Unsecured']]
        # Sort by Planner and Month
        pivot_df = pivot_df.sort_values(by=['Planner', 'Month']).reset_index(drop=True)

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

if __name__ == "__main__":
    main()



