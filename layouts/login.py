import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify

def create_login_layout():
    return html.Div([
        dmc.Grid([
            # Columna izquierda: Formulario
            dmc.GridCol([
                dmc.Center([
                    dmc.Paper([
                        dmc.Title("Inicia sesión en Dash", order=2, style={"marginBottom": 10, "textAlign": "center"}),
                        dmc.Text("Revisa tus indicadores", size="md", c="dimmed", style={"marginBottom": 20, "textAlign": "center"}),
                        dmc.TextInput(
                            id="username-input",
                            label="Username",
                            placeholder="edwardo97",
                            style={"width": "100%", "marginBottom": 10}
                        ),
                        dmc.PasswordInput(
                            id="password-input",
                            label="Contraseña",
                            placeholder="Ingresa tu contraseña",
                            style={"width": "100%", "marginBottom": 20}
                        ),
                        dmc.Button(
                            "Iniciar Sesión",
                            id="login-button",
                            variant="filled",
                            color="blue",
                            fullWidth=True,
                            style={"marginBottom": 10}
                        ),
                        #html.Div("o inicia sesión con", style={"textAlign": "center", "margin": "10px 0", "color": "#888"}),
                        #dmc.Group([
                        #    dmc.Button("", leftSection=DashIconify(icon="flat-ui:settings", width=30), variant="outline", color="blue", radius="xl"),
                        #    dmc.Button("", leftSection=DashIconify(icon="flat-ui:settings", width=30), variant="outline", color="red", radius="xl"),
                        #    dmc.Button("", leftSection=DashIconify(icon="flat-ui:settings", width=30), variant="outline", color="dark", radius="xl"),
                        #],  gap="md", style={"marginBottom": 10, "position": "center"}),
                        html.Div(id="login-error", style={"color": "red", "textAlign": "center", "marginBottom": 10}),
                        #html.Div([
                        #     html.Span("¿No tienes cuenta? "),
                        #    dmc.Anchor("Regístrate", href="#", c="blue", underline=True)
                        #], style={"textAlign": "center", "fontSize": 14, "marginTop": 10})
                    ], shadow="md", radius="lg", p=30, style={"width": 350, "background": "#fff", "maxWidth": "95vw"})
                ], style={"height": "100vh"})
            ], 
            span={"lg": 7, "md": 6, "sm": 12, "xs": 12},
            #md=7, sm=12, xs=12, 
            #order={"","md":7, "sm": 12, "xs": 12},
            style={"display": "flex", "alignItems": "center", "justifyContent": "center", "background": "#fff"}),
            # Columna derecha: Espacio para imagen
            dmc.GridCol([
                # Deja este div vacío para que puedas agregar tu imagen/fondo
                dmc.Image(
                    radius="md",
                    src=f'/resource/login.jpg',
                    style={"width": "100%", "height": "100%", "objectFit": "cover"},
                    
                )
            ], 
            #span=6, 
            #md=5, sm=0, xs=0, 
            span={"lg": 5, "md":5, "sm": 0, "xs": 0},
            style={"background": "#e0e7ff", "height": "100vh", "display": "block"})
        ], gutter=0, style={"minHeight": "100vh", "background": "#fff"})
    ])
