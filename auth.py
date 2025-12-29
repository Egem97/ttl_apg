import asyncio
import secrets
import yaml
import os
from datetime import datetime, timedelta
from functools import wraps
from flask_login import LoginManager, UserMixin
from flask import request, jsonify
from models import (
    DatabaseManager, 
    get_database_url, 
    get_user_by_username, 
    authenticate_user as auth_user_db,
    create_user_with_profile,
    create_user_session,
    get_user_session,
    invalidate_user_session,
    User as UserModel,
    Company as CompanyModel,
    UserRole
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from core.session_manager import init_session_manager, get_session_manager
from core.auth_middleware import init_auth_middleware, get_auth_middleware

# Initialize Flask-Login
login_manager = LoginManager()
