from pathlib import Path
import numpy as np
import pandas as pd
import folium
import json
from tqdm import tqdm
import branca.colormap as cm

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
        "Total",
    ],
)
election["PrecinctCountyCode"] = election["CountyID"].astype(str).str.zfill(2) + election["PrecinctID"].astype(str).str.zfill(4)

harris_lookup = (
    election[election["Party"] == "DFL"]
    .set_index("PrecinctCountyCode")
    .to_dict(orient="index")
)
trump_lookup = (
    election[election["Party"] == "R"]
    .set_index("PrecinctCountyCode")
    .to_dict(orient="index")
)

geojson_path = Path(__file__).parent / "mn-precincts.json"
geojson = json.loads(geojson_path.read_text())

to_delete = []
for feature in tqdm(geojson["features"]):
    county_id = f"{int(feature['properties']['CountyID']):02d}"
    precinct_code = feature["properties"]["PrecinctID"][-4:]
    new_code = f"{county_id}{precinct_code}"
    feature["properties"]["PrecinctCountyCode"] = new_code

    harris_data = harris_lookup.get(new_code)
    trump_data = trump_lookup.get(new_code)

    if harris_data and trump_data:
        feature["properties"]["Total"] = int(harris_data["Total"])
        feature["properties"]["HarrisPerc"] = float(harris_data["Perc"])
        feature["properties"]["HarrisVotes"] = int(harris_data["Votes"])
        feature["properties"]["TrumpPerc"] = float(trump_data["Perc"])
        feature["properties"]["TrumpVotes"] = int(trump_data["Votes"])
    else:
        to_delete.append(feature)

    for prop in [
        "PrecinctID",
        "County",
        "CountyID",
        "CongDist",
        "MNSenDist",
        "MNLegDist",
        "CtyComDist",
    ]:
        feature["properties"].pop(prop, None)

for feature in to_delete:
    geojson["features"].remove(feature)

# color_scale = cm.linear.RdBu_10.scale(0, 100)  # Adjust scale range as needed

bins = np.linspace(0, 100, 12)  # 11 bins from 0 to 100
color_scale = cm.StepColormap(
    colors=cm.linear.RdBu_11.colors,  # Use the RdBu colormap with 11 colors
    index=bins,
    vmin=0,
    vmax=100,
    caption="Percentage of Vote Won by DFL (%)",
)

m = folium.Map(location=[46.2, -93.093124], zoom_start=7)

def style_function(feature):
    total = feature["properties"].get("Total")
    harris_perc = feature["properties"].get("HarrisPerc")
    if total > 0:
        fill_color = color_scale(harris_perc)
    else:
        fill_color = "transparent"
    return {
        "fillColor": fill_color,
        "color": "black",
        "weight": 0.325,
        "fillOpacity": 0.7,
    }

geojson_layer = folium.GeoJson(
    geojson,
    style_function=style_function,
    tooltip=folium.GeoJsonTooltip(
        fields=[
            "Precinct",
            "HarrisVotes",
            "TrumpVotes",
            "HarrisPerc",
            "TrumpPerc",
            "Total",
        ],
        aliases=[
            "Precinct:",
            "Harris Votes:",
            "Trump Votes:",
            "Harris %:",
            "Trump %:",
            "Total Votes:",
        ],
        localize=True,
    ),
)

color_scale.caption = "Percentage of Vote Won by DFL (%)"
color_scale.add_to(m)
geojson_layer.add_to(m)

m.save(build_folder / "index.html")
