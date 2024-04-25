#Imports the correct libraries so I can use the functions
#that are within these libraries
import re
from unittest import mock
import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import W
from riotwatcher import LolWatcher, ApiError

# Function to dynamically fetch the latest patch note
def get_latest_version():
    response = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
    versions = response.json()
    return versions[0] if response.status_code == 200 else "14.8.1"

#Initializes the LolWatcher with API to authenticate requests
api_key_master = "RGAPI-4ca96f4c-7796-4581-a467-a98e60e5aabe"
region = "euw1"
latest_version = get_latest_version()
watcher = LolWatcher(api_key_master)

st.title("View.GG")

#Streamlit tabs used to seperate sections in a neat way :D
tab1, tab2, tab3 = st.tabs(["Summoner Information", "Champions", "Items"])

#Tab1 = Summoner information
#Used to fetch information of summoner based on user input
with tab1:
    summoner_name = st.text_input("Enter Summoner Name:")
    
    #Function to calculate winrate based of wins and total games api info gathered
    def calc_winrate(wins, total_games):
        return round((wins / total_games) * 100, 2) if total_games > 0 else 0

    #Function to collect last 20 games of summoner
    def match_history(summoner_puuid, match_region):
        outcomes = []
        try:
            match_ids = watcher.match.matchlist_by_puuid(match_region, summoner_puuid, count=20)
            for match_id in match_ids:
                match_details = watcher.match.by_id(match_region, match_id)
                participant_id = next(
                    (participant['participantId']
                     for participant in match_details['info']['participants']
                     if participant['puuid'] == summoner_puuid),
                    None
                )
                if participant_id is not None:
                    participant_info = next(
                        (participant for participant in match_details['info']['participants']
                         if participant['participantId'] == participant_id),
                        None
                    )
                    if participant_info:
                        win = participant_info['win']
                        outcomes.append("Win" if win else "Loss")
        except ApiError as err:
            print(f"API Error occurred: {err}")

        return outcomes

    
    #Streamlit display components
    if st.button("Get Summoner Info"):
        with st.spinner('Fetching summoner information...'):
            try:
                # Fetch summoner information
                summoner = watcher.summoner.by_name(region, summoner_name)
                updated_summoner_name = summoner.get('name')
                summoner_puuid = summoner['puuid']  # Extracting the puuid
                match_outcomes = match_history(summoner_puuid, 'EUROPE')
                
                col1, col2, = st.columns([1, 3])
                # Column 1 displays the summoner profile icon
                with col1:
                    profile_icon_id = summoner['profileIconId']
                    profile_icon_url = f"http://ddragon.leagueoflegends.com/cdn/{latest_version}/img/profileicon/{profile_icon_id}.png"
                    st.image(profile_icon_url, width=150)
                # Column 2 displays summoner information
                with col2:
                    st.write(f"Summoner Name: {summoner_name}")
                    st.write(f"Summoner Level: {summoner['summonerLevel']}")
                    
                # Fetches ranked solo queue stats of summoner
                ranked_stats = watcher.league.by_summoner("euw1", summoner['id'])
                solo_Q_stats = next((queue for queue in ranked_stats if queue['queueType'] == 'RANKED_SOLO_5x5'), None)
                if solo_Q_stats:
                    total_games = solo_Q_stats['wins'] + solo_Q_stats['losses']
                    winrate = calc_winrate(solo_Q_stats['wins'], total_games)
                    st.write(f"Season 14:")
                    st.write(f"Solo Queue Winrate: {winrate}%")
                else:
                    st.write("No Solo Queue ranked stats available.")
                
                # Fetches and displays last 20 match outcomes of summoner with line graph
                if match_outcomes:
                    outcomes_df = pd.DataFrame({"Match": range(1, 21), "Outcome": [1 if outcome == "Win" else 0 for outcome in match_outcomes]})
                    # Customizing the line graph plot
                    fig, ax = plt.subplots()
                    ax.plot(outcomes_df['Match'], outcomes_df['Outcome'], marker='o', linestyle='-', color='#0a84d7', markersize=8, alpha=0.7)
                    ax.set_title('Last 20 Match Outcomes', fontsize=14, color='#333333', fontweight='bold')
                    ax.set_xlabel('Match', fontsize=12, color='#333333')
                    ax.set_ylabel('Outcome', fontsize=12, color='#333333')
                    ax.set_xticks(outcomes_df['Match'])
                    ax.set_yticks([0, 1])
                    ax.set_yticklabels(['L', 'W'], fontsize=12)
                    ax.set_facecolor('white')
                    ax.grid(True, which='both', linestyle='--', linewidth=0.5, color='grey', alpha=0.3)
                    for spine in ax.spines.values():
                        spine.set_visible(False)
                    st.pyplot(fig)
                else:
                    st.write("Unable to fetch match history.")
            # Error handling to ensure user gets text instead of red error screen
            except ApiError as err:
                st.error(f"Failed to fetch summoner information: {err}")
          
with tab2:
    #st.cache makes it so the function doesnt have to scrape the api everytime to gather the champion data
    #If it has been loaded once, it will just store that data in cache and use that data
    @st.cache_resource
    #Function that fetches champion data from league of legends dragon api
    def fetch_champion_details(champion_name):
        champion_info = requests.get(f'http://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/champion/{champion_name}.json').json()['data']
        return champion_info[champion_name]

    #Fetch champion names from Data Dragon API
    def fetch_champion_names():
        response = requests.get(f'http://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/champion.json')
        if response.status_code == 200:
            return response.json()['data']
        else:
            st.error("Failed to fetch champion data.")
            return {}

    champion_info = fetch_champion_names()
    champion_names = {champ_name: champ_info['key'] for champ_name, champ_info in champion_info.items()}
    
    if champion_names:
        st.write("Choose a champion:")
        selected_champion_name = st.selectbox("Select champion", list(champion_names.keys()))
        champion = fetch_champion_details(selected_champion_name)
        st.subheader(champion['name'])
        
        col1, col2 = st.columns([1, 3])  # Adjust the ratio as needed
        with col1:
            st.image(f"http://ddragon.leagueoflegends.com/cdn/{latest_version}/img/champion/{champion['image']['full']}", width=150,)
        with col2:
            if 'lore' in champion:
                lore_html = f"""
                <style>
                .lore-font {{
                    font-size:18px !important;
                }}
                </style>
                <p class="lore-font">{champion['lore']}</p>
                """
                st.markdown(lore_html, unsafe_allow_html=True)
            else:
                st.write("No lore available.")

        st.write("**Abilities:**")
        for spell in champion['spells']:
        # Create two columns: one for the image, one for the text
            col1, col2 = st.columns([1, 3])  # Adjust the ratio as needed for your layout
        
            with col1:  # This column will contain the spell image
                st.image(f"http://ddragon.leagueoflegends.com/cdn/{latest_version}/img/spell/{spell['id']}.png", width=130)

            with col2:  # This column will contain the spell name and description
                st.markdown(f"**{spell['name']}**: {spell['description']}")
    else:
        st.write("Failed to fetch champion data.")
        
with tab3:
    #Function to fetch item details from data dragon api
    @st.cache_resource
    def fetch_item_details():
        item_info = requests.get(f'http://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/item.json')
        if item_info.status_code == 200:
            return item_info.json()['data']
        else:
            st.error("Failed to fetch item data.")
            return{}
        
    items_data = fetch_item_details()
    
    if items_data:
        item_names = [item['name'] for item_id, item in items_data.items()]
        selected_item_name = st.selectbox("Select an item: ", options=item_names)
        
        selected_item = next((item for item_id, item in items_data.items() if item['name'] == selected_item_name), None)
        
    def clean_html_tags(raw_html):
        """Replace HTML tags with spaces to prevent words from running together."""
        clean_text = re.sub('<[^>]+>', ' ', raw_html)  # Replace tags with a space
        clean_text = re.sub(' +', ' ', clean_text)  # Replace multiple spaces with a single space
        return clean_text.strip()

    def format_description(description):
        """Format the cleaned description for better readability."""
        # Insert line breaks for major sections of the description if needed
        description = description.replace('Mythic Passive:', '\n\n**Mythic Passive:**')
        description = description.replace('Active:', '\n\n**Active:**')
        description = description.replace('Passive:', '\n\n**Passive:**')
    
        # Further refine and clean the description
        cleaned_description = clean_html_tags(description)
    
        return cleaned_description

    if selected_item:
        col1, col2 = st.columns([1, 3])  # Adjust the ratio as needed for your layout

        with col1:  # This column will contain the item image
            if 'image' in selected_item and 'full' in selected_item['image']:
                st.image(f"http://ddragon.leagueoflegends.com/cdn/{latest_version}/img/item/{selected_item['image']['full']}", width=130)
    
        with col2:  # This column will contain the item name and description
            st.header(selected_item.get('name', 'No Name Found'))
        
            # Process and display the selected item's description
            formatted_description = format_description(selected_item.get('description', 'No description available'))
        
            st.markdown("**Description:**")
            st.markdown(formatted_description)
