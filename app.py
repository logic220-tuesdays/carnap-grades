import streamlit as st
import pandas as pd
from thefuzz import fuzz
from thefuzz import process
import re

st.title("CSV Processor")

st.write("Download grades from Carnap.io using the 'per assignment' option. (Make sure there are no repeated names in Carnap!)")
st.write("Export grades from Brightspace selecting only the following options:")
st.markdown("""
- Export grade items for all users
- Org Defined ID, Last Name, First Name, Group Membership,
- and the assignment quiz you want to put the grades for (only one!!!!) 
""")

# File uploads
file1 = st.file_uploader("Upload Carnap csv", type=['csv'])
file2 = st.file_uploader("Upload Brightspace csv", type=['csv'])

if file1 and file2:
    # Read CSVs
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)

    target = df2.columns[-2]

    number = re.search(r'\d+', target).group()
    source = ''

    multiplier = 0

    if 'Assignment' in target:
        source = 'assignment ' + str(number) + '.md'
        multiplier = 1  # doesn't touch the assignment grade later on before converting to Extending, etc.
    elif 'Quiz' in target:
        source = 'quiz ' + str(number) + '.md'
        multiplier = 10  # multiplies the quiz grade by 10 later on before converting to Extending, etc.


    def fuzzy_merge(df1, df2, left_on, right_on, threshold=80, limit=1):

        # Create combined keys for matching
        df1['_fuzzy_key'] = df1[left_on[0]].astype(str) + ' | ' + df1[left_on[1]].astype(str)
        df2['_fuzzy_key'] = df2[right_on[0]].astype(str) + ' | ' + df2[right_on[1]].astype(str)

        # Prepare results
        matches = []

        for idx1, row1 in df1.iterrows():
            key1 = row1['_fuzzy_key']

            # Find best matches in df2
            best_matches = process.extract(
                key1,
                df2['_fuzzy_key'].tolist(),
                scorer=fuzz.token_sort_ratio,
                limit=limit  # limit=1 gives back only best match
            )

            for match_key, score in best_matches:
                if score >= threshold:
                    # Find the matching row in df2
                    df2_match = df2[df2['_fuzzy_key'] == match_key].iloc[0]

                    # Combine the rows
                    result_row = {**row1.to_dict(), **df2_match.to_dict()}
                    matches.append(result_row)

        # Create result DataFrame
        result_df = pd.DataFrame(matches)

        return result_df


    result = fuzzy_merge(df1, df2,
                         left_on=['Last Name', 'First Name'],
                         right_on=['Last Name', 'First Name'],
                         threshold=80,
                         limit=1
                         )

    df_merged = df2.merge(
        result[['Last Name', 'First Name', source]],  # columns needed from first data frame
        on=['Last Name', 'First Name'],  # columns to match on second data frame
        how='left'  # keep all rows from df2
    )

    df2[target] = df_merged[source]  # update the target thing in second data frame with the info about the assignment

    for i in df2.index:
        if df2.at[i, target] * multiplier > 84:
            df2.at[i, target] = str('Extending')
        elif df2.at[i, target] * multiplier > 74:
            df2.at[i, target] = str('Proficient')
        elif df2.at[i, target] * multiplier > 64:
            df2.at[i, target] = str('Developing')
        elif df2.at[i, target] * multiplier > 0:
            df2.at[i, target] = str('Emerging')
        elif df2.at[i, target] * multiplier == 0:
            df2.at[i, target] = None

    TA_heading = 'TA Sections'  # this is the name of the column with the TA groups

    TA_sections = df2[TA_heading].unique()  # this creates a numpy array of the section names

    # This lists all the TA sections
    st.write('These are the TA sections:')
    counter = 0
    for item in TA_sections:
        counter += 1
        st.write(str(counter) + '. ' + item)

    # This asks you to select one of the sections
    num = st.number_input("Which section is yours? Enter the corresponding number.",
min_value=0,max_value=(len(TA_sections) + 1))

    df2 = df2[df2[TA_heading] == TA_sections[num - 1]]

    df2.drop('_fuzzy_key', axis=1, inplace=True)

#    df2.to_csv('output.csv', index=False)

    if st.button("Process"):
        csv = df2.to_csv(index=False)
        st.write("Don't forget to double-check the students without grades (the app might have missed something, like the stuff mentioned [here](https://github.com/logic220-tuesdays/carnap-grades/issues))")
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="output.csv",
            mime="text/csv"
        )
