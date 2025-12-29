import dash
import dash_mantine_components as dmc
import requests
from dash import html
from dash_iconify import DashIconify
from constants import PAGE_TITLE_PREFIX
from dash import Dash, dcc, html, Input, Output, dash_table, callback
from components.grid import Row, Column
import dash_mantine_components as dmc
import plotly.express as px
from components.cards import cardHome
#from core.bd import dataOut

dash.register_page(
    __name__,
    "/",
    title= PAGE_TITLE_PREFIX+ "Home",
    #description="Official documentation and collection of ready-made Plotly Dash Components created using Dash "
    #"Mantine Components. Dash Mantine Components is an extensive UI components library for Plotly Dash "
    #"with more than 90 components and supports dark theme natively.",
)

#df = dataOut()
layout = dmc.Container(
    fluid=True,
    #px=40,
    children=[
        dmc.Title("Home", order=1, mt=30),

        dmc.Text(
            "Consulta información clave",
            size="md",
            c="dimmed",
            mt=10,
            mb=30
        ),

    ]
)
"""
@callback(
    Output("line_chart", "figure"),
    Input("stock-dropdown", "value"),
)
def select_stocks(stocks):
    fig = px.line(data_frame=data, x="date", y=stocks, template="simple_white")
    fig.update_layout(
        margin=dict(t=50, l=25, r=25, b=25), yaxis_title="Price", xaxis_title="Date"
    )
    return fig


layout = html.Div(
    [
        dmc.Container(
            size="lg",
            mt=30,
            children = [
                dmc.Text("Version Info:"),
            ]
        ) 
    ]
)  
"""