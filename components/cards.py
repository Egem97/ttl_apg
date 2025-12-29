import dash_mantine_components as dmc
from dash_iconify import DashIconify


def cardHome(title, subtitle, badge, button_text, button_color,color_badge="green"):
    return dmc.Card(
                    children=[
                        dmc.CardSection(
                            dmc.Group(
                                    children=[
                                        dmc.Text(title, fw=700,size="lg",c="blue"),
                                        dmc.ActionIcon(
                                            DashIconify(icon="carbon:overflow-menu-horizontal"),
                                            color="gray",
                                            variant="transparent",
                                        ),
                                    ],
                                    justify="space-between",
                                ),
                                withBorder=True,
                                inheritPadding=True,
                                py="xs",
                        ),
                        dmc.Group(
                            [
                                dmc.Text(subtitle, fw=400),
                                dmc.Badge(badge, color=color_badge),
                            ],
                            justify="space-between",
                            mt="md",
                            mb="xs",
                        ),
                        dmc.Text(
                            "ww",
                            size="sm",
                            c="dimmed",
                        ),
                        dmc.Button(
                            button_text,
                            color=button_color,
                            fullWidth=True,
                            mt="md",
                            radius="md",
                            variant="light",
                        ),
                    ],
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    #w=350,
                )