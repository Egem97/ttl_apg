import dash_mantine_components as dmc
from dash_iconify import DashIconify
#from constants import LOGO
from flask_login import current_user

def create_header(data):
    return \
    dmc.AppShellHeader(
        dmc.Group(
            [
                dmc.Group(
                    [
                        dmc.Burger(
                            id="mobile-burger",
                            size="sm",
                            hiddenFrom="sm",
                            opened=False,
                        ),
                        dmc.Burger(
                            id="desktop-burger",
                            size="sm",
                            visibleFrom="sm",
                            opened=True,
                        ),
                        #dmc.Image(src=f'/resource', h=30, w=30),#/{LOGO}
                        dmc.Title("", c="black"),
                    ]
                ),
                dmc.Group(
                    [
                        dmc.Switch(
                            offLabel=DashIconify(
                                icon="radix-icons:sun", width=15, color=dmc.DEFAULT_THEME["colors"]["yellow"][8]
                            ),
                            onLabel=DashIconify(
                                icon="radix-icons:moon",
                                width=15,
                                color=dmc.DEFAULT_THEME["colors"]["yellow"][6],
                            ),
                            id="color-scheme-toggle",
                            persistence=True,
                            color="grey",
                        ),
                        #dmc.Text("Edwardo", fw=700),
                        
                        dmc.Menu(
                            [
                                dmc.MenuTarget(
                                    dmc.Avatar(
                                        src="https://th.bing.com/th/id/OIP.fexuorPLWDO56z_X9W9jiwAAAA?o=7&cb=ucfimg2&rm=3&ucfimg=1&rs=1&pid=ImgDetMain&o=7&rm=3",
                                        size="md",
                                        radius="xl",
                                    ),
                                ),
                                dmc.MenuDropdown(
                                    [
                                        dmc.MenuLabel("Application"),
                                        dmc.MenuItem(
                                            "Settings", leftSection=DashIconify(icon="tabler:settings")
                                        ),
                                        dmc.MenuItem(
                                            "Messages", leftSection=DashIconify(icon="tabler:message")
                                        ),
                                        dmc.MenuItem("Gallery", leftSection=DashIconify(icon="tabler:photo")),
                                        dmc.MenuItem("Search", leftSection=DashIconify(icon="tabler:search")),
                                        #dmc.MenuDivider(),
                                        #dmc.MenuLabel("Danger Zone"),
                                        #dmc.MenuItem(
                                        #    "Transfer my data",
                                        #    leftSection=DashIconify(icon="tabler:arrows-left-right"),
                                        #),
                                        dmc.MenuItem(
                                            "Cerrar sesión",
                                            leftSection=DashIconify(icon="tabler:logout"),
                                            color="red",
                                            id="logout-button",
                                        ),
                                    ]
                                ),
                            ],
                            trigger="hover",
                        ),
                        
                    ]
                )
                
            ],
            justify="space-between",
            style={"flex": 1},
            h="100%",
            px="sm",
        ),            
    )

