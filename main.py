from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import JWTError, jwt

import models
from database import engine, Base, get_db

# Configuración de Seguridad JWT (Llave secreta y algoritmo)
SECRET_KEY = 'clave_secreta_super_segura_para_nuestro_crm'
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Inicializar la app
app = FastAPI(title='CRM Pro JWT API', version='1.0')

# CORS para que React pueda conectarse sin problemas
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Passlib para encriptar contraseñas
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

# Funciones de ayuda para Password y JWT
def hash_password(password: str) -> str:
    # Aseguramos que la contraseña no supere los 72 bytes por limitación nativa de bcrypt
    safe_password = password.encode('utf-8')[:72]
    return pwd_context.hash(safe_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    safe_password = plain_password.encode('utf-8')[:72]
    return pwd_context.verify(safe_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Esquemas Pydantic
class UserCreate(BaseModel):
    nombre: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    nombre: str
    email: str

    class Config:
        from_attributes = True

# Inicializar tablas al arrancar
Base.metadata.create_all(bind=engine)

# Rutas de API
@app.get('/')
def read_root():
    return {'message': '¡Backend avanzado con JWT funcionando al 100%! 🚀'}

# 1. Ruta de Registro
@app.post('/register', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='El correo electrónico ya está registrado.'
        )
    
    new_user = models.User(
        nombre=user.nombre,
        email=user.email,
        hashed_password=hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# 2. Ruta de Login (Devuelve el Token JWT)
@app.post('/login')
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # form_data.username se mapea al email del usuario
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Credenciales incorrectas (correo o contraseña inválidos)',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={'sub': user.email}, expires_delta=access_token_expires
    )
    
    return {'access_token': access_token, 'token_type': 'bearer'}