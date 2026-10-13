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

# Funciones de ayuda para Password y JWT (Blindadas contra límite de 72 bytes de bcrypt)
def hash_password(password: str) -> str:
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

# Dependencia para validar y decodificar el Token JWT en rutas protegidas
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='No se pudo validar las credenciales',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get('sub')
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# Esquemas Pydantic para Usuarios
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

# Esquemas Pydantic para Clientes
class ClientCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None

class ClientResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None

    class Config:
        from_attributes = True

# Inicializar tablas en MySQL al arrancar
Base.metadata.create_all(bind=engine)

# Rutas de la API
@app.get('/')
def read_root():
    return {'message': '¡Backend avanzado con JWT y CRUD de Clientes funcionando al 100%! 🚀'}

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

# 2 Ruta de Login (Devuelve el Token JWT)
@app.post('/login')
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
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

# 3 Crud Clientes (Protegidas con JWT)
@app.get('/clients', response_model=list[ClientResponse])
def get_clients(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    clients = db.query(models.Client).filter(models.Client.owner_id == current_user.id).all()
    return clients

@app.post('/clients', response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(client: ClientCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    new_client = models.Client(
        name=client.name,
        email=client.email,
        phone=client.phone,
        owner_id=current_user.id
    )
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    return new_client

@app.put('/clients/{client_id}', response_model=ClientResponse)
def update_client(client_id: int, client: ClientCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_client = db.query(models.Client).filter(models.Client.id == client_id, models.Client.owner_id == current_user.id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail='Cliente no encontrado')
    
    db_client.name = client.name
    db_client.email = client.email
    db_client.phone = client.phone
    db.commit()
    db.refresh(db_client)
    return db_client

@app.delete('/clients/{client_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_client = db.query(models.Client).filter(models.Client.id == client_id, models.Client.owner_id == current_user.id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail='Cliente no encontrado')
    
    db.delete(db_client)
    db.commit()
    return {'ok': True}