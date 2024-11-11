from pathlib import Path
import pandas as pd
import folium
import json
from tqdm import tqdm

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

m = folium.Map(location=[46.2, -93.093124], zoom_start=7)
choropleth = folium.Choropleth(
    geo_data=geojson,
    data=election[election["Party"] == "DFL"],
    columns=["PrecinctCountyCode", "Perc"],
    key_on="feature.properties.PrecinctCountyCode",
    fill_color="RdBu",
    fill_opacity=0.7,
    bins=10,
    overlay=True,
    legend_name="Percentage of Vote Won by DFL (%)",
)
geojson_layer = folium.GeoJson(
    geojson,
    tooltip=folium.GeoJsonTooltip(
        fields=[
            "PrecinctCountyCode",
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
    style_function=lambda x: {"fillOpacity": 0, "color": "transparent"},
)

choropleth.add_to(m)
geojson_layer.add_to(m)

m.save(build_folder / "index.html")
