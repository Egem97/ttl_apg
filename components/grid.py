import plotly.express as px
import dash_mantine_components as dmc

def Row(content = [],g = "xs"):
    return \
    dmc.Grid(
        children = content,
        gutter= g
    )

def Column(content = [], size = 12):
    return \
    dmc.GridCol(  
        children = content,
        span={"base": 12, "md": size, "lg":size}

    )