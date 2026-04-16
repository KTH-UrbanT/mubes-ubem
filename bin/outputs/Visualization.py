

from dash import Dash, dcc, html, Input, Output, callback
import os,sys
import pickle
from bin.outputs import output_utilities
import core.GeneralFunctions as GrlFct
import building_geometry.BuildingObject as BuildingObject
import pandas as pd
import numpy as np
import json
import pickle

def Visualization(ResultPath):
    # -------------------------------------------------
    # LOAD RESULTS (MULTIPLE BUILDINGS)
    # -------------------------------------------------
    results_by_building = {}

    # ResultPath = '../../examples/NUS0/Sim_Results/'
    files = os.listdir(os.path.join(ResultPath, 'Sim_Results'))

    for bld in files:
        if bld.endswith('.pickle'):
            with open(os.path.join(ResultPath, bld), 'rb') as f:
                results_by_building[bld] = pickle.load(f)

    assert isinstance(results_by_building, dict)

    # -------------------------------------------------
    # APP
    # -------------------------------------------------
    app = Dash(__name__)

    app.layout = html.Div(
        style={"width": "80%", "margin": "auto"},
        children=[

            # ================= HEADER =================
            html.Div(
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "marginBottom": "25px"
                },
                children=[
                    html.Img(
                        src="/assets/MUBESPNG.png",
                        style={"height": "60px", "marginRight": "12px"}
                    ),
                    html.H3("EnergyPlus / UBEM Results Explorer", style={"margin": "0"})
                ]
            ),

            # ================= BUILDING =================
            html.Label("Building"),
            dcc.Dropdown(
                id="building",
                options=[{"label": b[:b.find('.pickle')], "value": b} for b in results_by_building.keys()],
                placeholder="Select building"
            ),

            html.Br(),

            # ================= CATEGORY =================
            html.Label("Category"),
            dcc.Dropdown(
                id="category",
                placeholder="Select category"
            ),

            html.Br(),

            # ================= RESULT =================
            html.Label("Result"),
            dcc.Dropdown(
                id="result",
                placeholder="Select result"
            ),

            html.Br(),

            # ================= PLOT TYPE =================
            html.Label("Plot type"),
            dcc.RadioItems(
                id="plot-type",
                options=[
                    {"label": "Line", "value": "line"},
                    {"label": "Bar", "value": "bar"}
                ],
                value="line",
                inline=True
            ),

            html.Br(),
            html.Br(),

            # ================= GRAPH =================
            dcc.Graph(id="graph"),

            html.Hr(),

            # ================= DEBUG =================
            html.Details([
                html.Summary("Raw data (debug)"),
                dcc.Markdown(id="debug")
            ])
        ]
    )

    # -------------------------------------------------
    # CALLBACK 1: update Category based on Building
    # -------------------------------------------------
    @callback(
        Output("category", "options"),
        Output("category", "value"),
        Input("building", "value")
    )
    def update_category_dropdown(building):

        if building is None:
            return [], None

        results = results_by_building[building]

        categories = [
            k for k in results.keys()
            if "BuildDB" not in k
            and "OutdoorSurfacesNames" not in k
            and "ExtEnvSurf" not in k
            and "IntVolume" not in k
        ]

        options = [{"label": k, "value": k} for k in categories]
        return options, categories[0]


    # -------------------------------------------------
    # CALLBACK 2: update Result based on Building + Category
    # -------------------------------------------------
    @callback(
        Output("result", "options"),

        Output("result", "value"),
        Input("building", "value"),
        Input("category", "value")
    )
    def update_result_dropdown(building, category):

        if building is None or category is None:
            return [], None

        results = results_by_building[building]
        keys = results[category].keys()

        options = [
            {"label": k, "value": k}
            for k in keys
            # if "Unit" not in k and "TimeStep" not in k
        ]

        return options, options[0]["value"]


    # -------------------------------------------------
    # CALLBACK 3: update Graph
    # -------------------------------------------------
    @callback(
        Output("graph", "figure"),
        Output("debug", "children"),
        Input("building", "value"),
        Input("category", "value"),
        Input("result", "value"),
        Input("plot-type", "value")
    )
    def update_graph(building, category, result_key, plot_type):

        if None in (building, category, result_key):
            return {}, ""

        results = results_by_building[building]
        data = results[category][result_key]
        unit_key = f"Unit_{result_key[result_key.find('_')+1:]}"
        unit = results[category].get(unit_key, "")

        # ---- unit lookup ----
        # unit = results[category].get(f"{result_key}_Unit", "")

        # ---- normalize data ----
        if isinstance(data, pd.Series):
            x, y = data.index.tolist(), data.values.tolist()
            debug = data.head().to_string()

        elif isinstance(data, pd.DataFrame):
            x, y = data.index.tolist(), data.iloc[:, 0].tolist()
            debug = data.head().to_string()

        elif isinstance(data, dict):
            x, y = list(data.keys()), list(data.values())
            debug = json.dumps(dict(list(data.items())[:5]), indent=2)

        elif isinstance(data, (list, np.ndarray)):
            x, y = list(range(len(data))), list(data)
            debug = json.dumps(y[:5], indent=2)

        else:
            fig = {
                "data": [{"x": [result_key], "y": [data], "type": "bar"}],
                "layout": {"title": result_key}
            }
            return fig, f"```\n{json.dumps(data, indent=2)}\n```"

        trace = {
            "x": x,
            "y": y,
            "type": "scatter" if plot_type == "line" else "bar",
            "mode": "lines" if plot_type == "line" else None
        }

        fig = {
            "data": [trace],
            "layout": {
                "title": {"text": result_key[result_key.find('_')+1:], "x": 0.5},
                "xaxis": {"title": "Time step"},
                "yaxis": {"title": {"text": f"({unit})" if unit else result_key, "font": {"size": 14}}},
                "margin": {"t": 60}
            }
        }

        return fig, f"```\n{debug}\n```"

    return app


# # -------------------------------------------------
# if __name__ == "__main__":
#     app.run(debug=True)
