from pathlib import Path
import pandas as pd
import folium
import json

build_folder = Path(__file__).parent / "build"
build_folder.mkdir(exist_ok=True)

election = pd.read_csv(
    "USPresPct.txt", 
    delimiter=";",
    names=[
        "State",
        "CountyID",
        "PrecinctID",
        "OfficeID",
        "OfficeName",
        "NA1",
        "COC",
        "CandidateName",
        "NA2",
        "NA3",
        "Party",
        "NA4",
        "NA5",
        "Votes",
        "Perc",
        "Total"
    ],
)
election['PrecinctCountyCode'] = (
    election['CountyID'].astype(str).str.zfill(2) + 
    election['PrecinctID'].astype(str).str.zfill(4)
)
election_filtered = election[(election["Party"] == "DFL")]

geojson_path = Path(__file__).parent / "mn-precincts.json"
geojson = json.loads(geojson_path.read_text())

to_delete = []
for feature in geojson["features"]:
    county_id = int(feature["properties"]["CountyID"])
    county_id = f"{county_id:02d}"
    vtdid = feature["properties"]["PrecinctID"]
    precinct_code = vtdid[-4:]

    new_code = f"{county_id}{precinct_code}"
    feature["properties"]["PrecinctCountyCode"] = new_code

    election_data = election_filtered[election_filtered["PrecinctCountyCode"] == new_code].iloc[0]
    feature["properties"]["Total"] = int(election_data["Total"])
    feature["properties"]["Votes"] = int(election_data["Votes"])
    feature["properties"]["Perc"] = float(election_data["Perc"])
    if election_data.Total == 0:
        to_delete.append(feature)

for feature in to_delete:
    geojson["features"].remove(feature)

m = folium.Map(location=[46.2, -93.093124], zoom_start=7)


choropleth = folium.Choropleth(
    geo_data=geojson,
    data=election_filtered,
    columns=['PrecinctCountyCode', 'Perc'],
    key_on='feature.properties.PrecinctCountyCode',
    fill_color='RdBu',
    fill_opacity=0.7,
    bins=10,
    overlay=True,
    legend_name='Percentage of Vote Won by DFL (%)'
)

geojson_layer = folium.GeoJson(
    geojson,
    tooltip=folium.GeoJsonTooltip(
        fields=['PrecinctCountyCode', 'Votes', 'Perc', 'Total'],
        aliases=['Precinct Code:', 'DFL Votes:', 'DFL %:', 'Total Votes:'],
        localize=True
    ),
    style_function=lambda x: {
        'fillOpacity': 0,  # Transparent fill so it won't override the Choropleth
        'color': 'transparent'  # Transparent border
    }
)

choropleth.add_to(m)
geojson_layer.add_to(m)


m.save(build_folder / "index.html")
