import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import requests
from bs4 import BeautifulSoup

def load_gemeentes():
    """Load Dutch gemeentes from Wikipedia"""
    try:
        # Wikipedia page URL for Dutch municipalities
        url = "https://nl.wikipedia.org/wiki/Lijst_van_Nederlandse_gemeenten"
        
        # Get the page content
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the main table with municipalities
        table = soup.find('table', {'class': 'wikitable'})
        
        # Extract gemeente names from the table (first column)
        gemeentes = []
        for row in table.find_all('tr')[1:]:  # Skip header row
            columns = row.find_all(['td', 'th'])
            if columns:
                # Get first column text, remove footnote references [1], [2] etc.
                gemeente_name = ''.join(filter(lambda x: not x.isdigit() and x not in '[]', columns[0].text.strip()))
                if gemeente_name:
                    gemeentes.append(gemeente_name)
        
        if debug_mode:
            st.write(f"Found {len(gemeentes)} gemeentes:")
            st.write(gemeentes[:5])  # Show first 5 for verification
            
        return sorted(gemeentes)
        
    except Exception as e:
        st.error(f"Error loading gemeentes: {str(e)}")
        st.write("Error details:", str(e))
        return ["Error loading gemeentes"]

# Add debug mode as a global variable
debug_mode = False

def main():
    st.set_page_config(page_title="ZoningKing - Ontwikkelkansen", layout="wide")
    
    # Header
    st.title("🏗️ ZoningKing - Ontwikkelkansen per Gemeente")
    
    # Debug mode toggle
    with st.sidebar:
        global debug_mode
        debug_mode = st.checkbox("Debug Mode", value=False)
    
    # Load gemeentes
    if debug_mode:
        st.write("Loading gemeentes from Wikipedia...")
    gemeentes = load_gemeentes()
    
    # Main interface
    with st.sidebar:
        st.header("Filters")
        
        # Gemeente selector with search
        selected_gemeente = st.selectbox(
            "Gemeente",
            options=gemeentes,
            index=gemeentes.index('Amsterdam') if 'Amsterdam' in gemeentes else 0,
            help="Selecteer een gemeente om de ontwikkelkansen te bekijken"
        )
        
        # Development type filter
        type_filter = st.multiselect(
            "Type ontwikkeling",
            [
                "Transformatie bestaand vastgoed",
                "Herontwikkeling terrein",
                "Nieuwbouw op vrije kavel",
                "Bestemmingswijziging mogelijk"
            ],
            default=["Transformatie bestaand vastgoed"]
        )
        
        # Area filter
        min_size = st.slider(
            "Minimale grootte (m²)", 
            min_value=0, 
            max_value=10000, 
            value=500, 
            step=100
        )
        
        # Status filter
        vergunning_status = st.multiselect(
            "Status in gemeenteplannen",
            [
                "Expliciet genoemd als ontwikkellocatie",
                "In omgevingsvisie als kansgebied",
                "Vergunning mogelijk volgens bestemmingsplan",
                "Wijziging bestemmingsplan nodig"
            ]
        )
        
        if st.button("Zoek Ontwikkelkansen", type="primary"):
            st.info(f"Zoeken naar kansen in {selected_gemeente}...")
            
            # Here we would trigger the scraping of zoning documents
            st.warning("Scanning gemeente documenten...")
    
    # Main content area with tabs
    tab1, tab2 = st.tabs(["Kaart & Details", "Ontwikkelkansen Lijst"])
    
    with tab1:
        map_col, details_col = st.columns([2, 1])
        
        with map_col:
            # Initialize map
            m = folium.Map(location=[52.3676, 4.9041], zoom_start=7)
            st_folium(m, height=600)
            
        with details_col:
            st.subheader(f"Details {selected_gemeente}")
            
            # Add gemeente info
            with st.expander("📋 Gemeente Informatie", expanded=True):
                st.write(f"**Gemeente:** {selected_gemeente}")
                
                # Add links to relevant municipal pages
                st.write("**Relevante Links:**")
                # Convert gemeente name to lowercase and remove spaces for URL
                gemeente_url = selected_gemeente.lower().replace(" ", "")
                st.write(f"- [Omgevingsvisie {selected_gemeente}](https://www.{gemeente_url}.nl/omgevingsvisie)")
                st.write(f"- [Bestemmingsplannen](https://www.ruimtelijkeplannen.nl)")
                
                st.write("**Status:** Scanning voor ontwikkelkansen...")
                st.write("**Laatste update:** ", datetime.now().strftime("%Y-%m-%d"))
    
    with tab2:
        st.subheader("Ontwikkelkansen Overzicht")
        if st.button("🔄 Ververs Kansen"):
            st.info("Ontwikkelkansen worden ververst...")
        
        # Placeholder for opportunities table
        placeholder_data = {
            'Locatie': ['Nog geen locaties gevonden'],
            'Type': ['-'],
            'Grootte': ['-'],
            'Status': ['-'],
            'Score': [0]
        }
        df = pd.DataFrame(placeholder_data)
        st.dataframe(df, hide_index=True)

if __name__ == "__main__":
    main()