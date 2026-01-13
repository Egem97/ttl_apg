import dash_mantine_components as dmc
from dash import Output, Input,State, clientside_callback
from dash_iconify import DashIconify
from utils import get_icon


def create_navbar(data):
    #if data['tipo_empresa'] == "COMERCIAL" or data['tipo_empresa'] == "Comercial":
        return \
        dmc.AppShellNavbar(
            id="navbar",
            children=[
                dmc.NavLink(
                            label="Home",
                            id = "navlink-home",
                            active="exact",
                            href="/",
                            leftSection=get_icon(icon="tabler:home"),
                        ),
                dmc.NavLink(
                    label="Recepcion MP",
                    leftSection=get_icon(icon="tabler:shield-dollar"),
                    childrenOffset=28,
                    children=[
                        dmc.NavLink(
                            label="Recepcion MP",
                            id = "navlink-dashboard",
                            active="exact",
                            #href="/costos-diarios"
                        ),
                        dmc.NavLink(
                            label="Devolucion Materiales",
                            id = "navlink-dashboard",
                            active="exact",
                            href="/devolucion-materiales"
                        ),
                        
                        #dmc.NavLink(label="Second child link"),
                        #dmc.NavLink(
                        #    label="Nested parent link",
                        #    childrenOffset=28,
                        #    children=[
                        #        dmc.NavLink(label="First child link"),
                        #        dmc.NavLink(label="Second child link"),
                        #        dmc.NavLink(label="Third child link"),
                        #    ],
                        #),
                    ],
                ),
                dmc.NavLink(
                    label="Gestión Humana",
                    leftSection=get_icon(icon="tabler:timeline-event"),
                    childrenOffset=28,
                    opened=False,
                    children=[
                        dmc.NavLink(
                            leftSection=get_icon(icon="tabler:users"),
                            label="Asistencia",
                            id = "navlink-dashboard",
                            active="exact",
                            href="/packing/gh_asistencia"
                        ),
                    ],
                ),
                dmc.NavLink(
                    label="Generador QR",
                    leftSection=get_icon(icon="tabler:qrcode"),
                    childrenOffset=28,
                    href="/packing/qr_generator",
                    opened=False,
                ),
                dmc.NavLink(
                    label="Transformación Data",
                    leftSection=get_icon(icon="tabler:table"),
                    childrenOffset=28,
                    opened=False,
                    children=[
                        dmc.NavLink(
                            leftSection=get_icon(icon="tabler:data-table"),
                            label="Materia Prima",
                            id = "navlink-dashboard",
                            active="exact",
                            href="/apg/transform-materia-prima"
                        ),
                    ],
                ),
            ],
            p=0,
        )
    