import dash_mantine_components as dmc
import dash
from dash import Dash, _dash_renderer, html, dcc
from constants import * 
from layouts.appshell import create_appshell
from layouts.login import create_login_layout

from dash.dependencies import Input, Output, State
import os
from datetime import datetime
from flask import send_from_directory, request, jsonify
#from core.bd import dataOut
#_dash_renderer._set_react_version("18.2.0")


data = {
    'name_user':NAME_USER,
    'name_empresa':NAME_EMPRESA,
    'tipo_empresa':RUBRO_EMPRESA,
}
scripts = [
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/dayjs.min.js",      # dayjs  
    "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.10.8/locale/fr.min.js",  # french locale
]
app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    use_pages=True,
    external_stylesheets=[dmc.styles.ALL]+scripts,
    update_title=False,
    assets_folder='assets',  # Asegurarse de que assets_folder apunte a la carpeta correcta
    title="Packing Tools"
)

# Configurar ruta específica para el favicon
@app.server.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.server.root_path, 'assets'),
        'favicon.ico',
        mimetype='image/x-icon'
    )

# Configurar la ruta para servir archivos desde resource
@app.server.route('/resource/<path:path>')
def serve_resource(path):
    return send_from_directory('resource', path)

# Configurar la clave secreta para Flask
#app.server.secret_key = os.environ.get('SECRET_KEY', 'una-clave-secreta-muy-segura-123')  # En producción, usa una clave segura desde variables de entorno



# Layout condicional
app.layout = dmc.MantineProvider(
    forceColorScheme="dark",
    #theme={
    #    "primaryColor": "cyan",
    #    "defaultRadius": "xl",
    #    "components": {
    #        "Card": {
    #            "defaultProps": {
    #                "shadow": "sm"
    #            }
    #        }
    #    }
    #},
    children=[
    html.Div(
        children=[
            html.Link(
                rel='icon',
                href='/assets/favicon.ico',
                type='image/x-icon'
            ),
            dcc.Location(id='url', refresh=False),
            html.Div(id='page-content')
        ]
    )
    ]
)

@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    # Verificar si el usuario tiene una sesión válida
    session_id = None
    
    # En Dash, no tenemos acceso directo a request, así que por ahora
    # mostraremos siempre el login. En producción, esto se manejaría
    # con JavaScript del lado cliente
    
    #if pathname == '/login' or pathname is None or pathname == '/':
    #    # Mostrar página de login
    #    return create_login_layout()
    
    # Si hay una sesión válida, mostrar el dashboard
    # Por ahora, siempre mostrar el dashboard después del login
    return create_appshell(data)
"""
@app.callback(
    [Output('url', 'pathname'),
     Output('login-error', 'children')],
    [Input('login-button', 'n_clicks')],
    [State('username-input', 'value'),
     State('password-input', 'value')]
)
def login_callback(n_clicks, username, password):
    if n_clicks is None:
        return '/login', ''
    
    if not username or not password:
        return '/login', 'Por favor ingrese usuario y contraseña'
    
    # Usar la nueva función de autenticación con Redis
    auth_result = authenticate_user(username, password)
    
    if auth_result:
        # Login exitoso - redirigir al dashboard
        # En producción, aquí se establecería la cookie de sesión
        # mediante JavaScript del lado cliente
        return '/dashboard', ''
    else:
        return '/login', 'Usuario o contraseña incorrectos'
@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    [Input('logout-button', 'n_clicks')],
    prevent_initial_call=True
)
def logout_callback(n_clicks):
    if n_clicks:
        logout_user()
        return '/login'
    return dash.no_update

@app.server.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not all(k in data for k in ('username', 'password', 'first_name', 'last_name', 'email')):
        return jsonify({'message': 'Missing required fields'}), 400
    
    success = create_user(
        username=data['username'],
        password=data['password'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
        phone=data.get('phone', ''),
        company_id=data.get('company_id', 1),  # Default company ID
        is_admin=data.get('is_admin', False)
    )
    
    if success:
        return jsonify({'message': 'User created successfully'}), 201
    else:
        return jsonify({'message': 'Username or email already exists'}), 400

@app.server.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not all(k in data for k in ('username', 'password')):
        return jsonify({'message': 'Missing username or password'}), 400
    
    result = authenticate_user(data['username'], data['password'])
    
    if result:
        # Crear respuesta con cookie de sesión
        response = jsonify({
            'message': 'Login successful',
            'user': {
                'user_id': result['user_id'],
                'username': result['username'],
                'email': result['email'],
                'company_id': result['company_id'],
                'company_name': result['company_name'],
                'role': result['role'],
                'is_admin': result['is_admin'],
                'full_name': result['full_name']
            }
        })
        
        # Establecer cookie de sesión
        response.set_cookie(
            'session_id', 
            result['session_id'],
            httponly=True,
            secure=True,  # Solo HTTPS en producción
            samesite='Lax',
            max_age=28800  # 8 horas
        )
        
        return response, 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401

@app.server.route('/logout', methods=['POST'])
@session_required
def logout():
    
    session_id = request.cookies.get('session_id') or request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if logout_user_session(session_id):
        response = jsonify({'message': 'Logout successful'})
        response.set_cookie('session_id', '', expires=0)  # Limpiar cookie
        return response, 200
    else:
        return jsonify({'message': 'Logout failed'}), 500

@app.server.route('/session', methods=['GET'])
@session_required
def get_session():
    
    session_data = request.session_data
    
    return jsonify({
        'user_id': session_data.user_id,
        'username': session_data.username,
        'email': session_data.email,
        'company_id': session_data.company_id,
        'company_name': session_data.company_name,
        'role': session_data.role,
        'is_admin': session_data.is_admin,
        'full_name': session_data.full_name,
        'created_at': session_data.created_at,
        'last_activity': session_data.last_activity
    }), 200

@app.server.route('/companies', methods=['GET'])
@session_required
def get_companies():
    
    session_data = request.session_data
    companies = get_user_companies(session_data.user_id)
    return jsonify(companies), 200

@app.server.route('/health', methods=['GET'])
def health_check():
    
    try:
        # Verificaciones básicas de salud
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'services': {
                'dashboard': 'running',
                'database': 'connected' if check_db_connection() else 'disconnected',
                'redis': 'connected' if check_redis_connection() else 'disconnected'
            }
        }
        
        # Agregar estadísticas de Redis si está disponible
        if check_redis_connection():
            try:
                redis_stats = session_manager.get_session_stats()
                health_data['redis_stats'] = redis_stats
            except Exception:
                pass
        
        # Determinar estado general
        all_services_healthy = all(
            status == 'connected' or status == 'running' 
            for status in health_data['services'].values()
        )
        
        if not all_services_healthy:
            health_data['status'] = 'degraded'
            return jsonify(health_data), 503
        
        return jsonify(health_data), 200
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

def check_db_connection():
    
    try:
        from auth import db_manager
        # Verificar conexión básica
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def test_connection():
            async with db_manager.get_session() as session:
                result = await session.execute("SELECT 1")
                return result.scalar() == 1
        
        result = loop.run_until_complete(test_connection())
        loop.close()
        return result
    except Exception as e:
        print(f"Database health check failed: {e}")
        return False

def check_redis_connection():
    
    try:
        session_manager.redis_client.ping()
        return True
    except Exception as e:
        print(f"Redis health check failed: {e}")
        return False
"""
if __name__ == "__main__":
    app.run(
        host='0.0.0.0',  # Permite conexiones desde cualquier IP
        port=PORT,       # Puerto personalizable
        debug=MODE_DEBUG,

    )