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
                            leftSection=get_icon(icon="tabler:home")
                ),
               
                dmc.NavLink(
                    label="Finanzas",
                    leftSection=get_icon(icon="tabler:table"),
                    childrenOffset=28,
                    opened=False,
                    children=[
                        dmc.NavLink(
                            leftSection=get_icon(icon="tabler:data-table"),
                            label="TXT Detracciones",
                            id = "navlink-dashboard",
                            active="exact",
                            href="/apg/txt_detracciones"
                        ),
                        dmc.NavLink(
                            leftSection=get_icon(icon="tabler:data-table"),
                            label="Sunat Oracle Det",
                            id = "navlink-dashboard",
                            active="exact",
                            href="/apg/sunat_oracle_det"
                        ),
                        dmc.NavLink(
                            leftSection=get_icon(icon="tabler:data-table"),
                            label="Conciliación T",
                            id = "navlink-bcp-oracle",
                            active="exact",
                            href="/apg/conciliacion-transform"
                        ),
                        dmc.NavLink(
                            leftSection=get_icon(icon="tabler:bank"),
                            label="TXT Pagos Proveedores",
                            id = "navlink-pagos-proveedores",
                            active="exact",
                            href="/apg/pagos_proveedores"
                        ),
                    ],
                ),
                dmc.NavLink(
                    label="Almacen",
                    leftSection=get_icon(icon="tabler:table"),
                    childrenOffset=28,
                    opened=False,
                    children=[
                        dmc.NavLink(
                            leftSection=get_icon(icon="tabler:data-table"),
                            label="Materia Prima",
                            id = "navlink-Almacen",
                            active="exact",
                            href="/apg/transform-materia-prima"
                        ),

                    ],
                ),
                dmc.NavLink(
                    label="Costos",
                    leftSection=get_icon(icon="tabler:table"),
                    childrenOffset=28,
                    opened=False,
                    children=[
                        dmc.NavLink(
                            leftSection=get_icon(icon="tabler:table-import"),
                            label="Transform Oracle Mapping",
                            id = "navlink-transform-oracle-mapping",
                            active="exact",
                            href="/costos/transform-oracle-mapping"
                        ),
                    ],
                ),

            ],
            p=0,
        )
    