import os
from typing import List
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from contextlib import asynccontextmanager
import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta

from database import create_db_and_tables, get_session
from models import User, Course, Note

# Configurazione per la sicurezza e i Token JWT
SECRET_KEY = "la_tua_chiave_segreta_super_sicura_da_cambiare"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # Durata del token (24 ore)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(title="Uni Study Hub API - Multiutente", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- FUNZIONI DI SUPPORTO PER LA SICUREZZA ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Dipendenza per ottenere l'utente attualmente loggato tramite il Token
def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenziali di accesso non valide",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise credentials_exception
    return user


# --- ENDPOINT DI AUTENTICAZIONE (Signup & Login) ---

@app.post("/signup/")
def register_user(username: str = Form(...), password: str = Form(...), session: Session = Depends(get_session)):
    existing_user = session.exec(select(User).where(User.username == username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Questo nome utente è già registrato.")
    
    hashed_password = get_password_hash(password)
    new_user = User(username=username, hashed_password=hashed_password)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    return {"message": f"Utente '{username}' registrato con successo!"}

@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome utente o password errati",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# --- GESTIONE CORSI (Isolati per utente) ---

@app.get("/courses/", response_model=list[Course])
def read_courses(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    courses = session.exec(select(Course).where(Course.user_id == current_user.id)).all()
    return courses


# --- GESTIONE APPUNTI (Isolati per utente) ---

@app.post("/notes/upload-folder/")
def upload_folder(
    course_name: str = Form(...),
    difficulty_level: int = Form(1),
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(Course).where(Course.name == course_name, Course.user_id == current_user.id)
    course = session.exec(statement).first()

    if not course:
        course = Course(name=course_name, status="in studio", user_id=current_user.id)
        session.add(course)
        session.commit()
        session.refresh(course)

    saved_notes = []
    for file in files:
        file_path = os.path.join(UPLOAD_DIR, f"{current_user.id}_{file.filename}")
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())

        db_note = Note(
            title=file.filename,
            file_path=file_path,
            difficulty_level=difficulty_level,
            course_id=course.id
        )
        session.add(db_note)
        saved_notes.append(db_note)

    session.commit()
    return {"message": f"Caricati {len(saved_notes)} file per il corso '{course.name}'!", "count": len(saved_notes)}

@app.get("/notes/", response_model=list[Note])
def read_notes(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    courses = session.exec(select(Course).where(Course.user_id == current_user.id)).all()
    course_ids = [c.id for c in courses]
    
    if not course_ids:
        return []
        
    notes = session.exec(select(Note).where(Note.course_id.in_(course_ids))).all()
    return notes