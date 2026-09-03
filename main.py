import os
import random
from typing import List
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from contextlib import asynccontextmanager
import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta
import resend

from database import create_db_and_tables, get_session
from models import User, Course, Note

SECRET_KEY = "la_tua_chiave_segreta_super_sicura_da_cambiare"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# Imposta la chiave API di Resend dalle variabili d'ambiente di Render
resend.api_key = os.environ.get("RESEND_API_KEY", "la_tua_resend_api_key")

# Dizionario temporaneo per i codici di verifica in attesa di conferma
VERIFICATION_CODES = {}

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

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenziali di accesso non valide",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None:
        raise credentials_exception
    return user

@app.post("/signup")
def register_user(username: str = Form(...), email: str = Form(...), password: str = Form(...), session: Session = Depends(get_session)):
    existing_user = session.exec(select(User).where((User.email == email) | (User.username == username))).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email o Nome Utente già registrati.")
    
    hashed_password = get_password_hash(password)
    new_user = User(username=username, email=email, hashed_password=hashed_password)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    return {"message": f"Utente '{username}' registrato con successo!"}

# Step 1: Verifica email/password e invia l'email reale con il codice OTP
@app.post("/login-request")
def login_request(username: str = Form(...), password: str = Form(...), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == username)).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email o password errati.")
    
    # Genera codice a 6 cifre
    code = str(random.randint(100000, 999999))
    VERIFICATION_CODES[username] = code
    
    # Invia l'email tramite Resend
    try:
        params = {
            "from": "Uni Study Hub <onboarding@resend.dev>",
            "to": [username],
            "subject": "Codice di verifica accesso - Uni Study Hub",
            "html": f"""
                <div style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2>Uni Study Hub 📚</h2>
                    <p>Hai richiesto di effettuare l'accesso. Il tuo codice di verifica è:</p>
                    <h1 style="color: #4F46E5; letter-spacing: 2px;">{code}</h1>
                    <p>Il codice è valido solo per questa sessione.</p>
                </div>
            """,
        }
        resend.Emails.send(params)
    except Exception as e:
        print(f"Errore invio email: {e}")
        raise HTTPException(status_code=500, detail="Impossibile inviare l'email di verifica.")
    
    return {"message": "Codice di verifica inviato via email."}

# Step 2: Conferma il codice inserito dall'utente e rilascia il token
@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    email = form_data.username
    entered_code = form_data.password
    
    expected_code = VERIFICATION_CODES.get(email)
    
    if not expected_code or expected_code != entered_code:
        raise HTTPException(status_code=401, detail="Codice di verifica non valido o scaduto.")
    
    # Rimuovi il codice usato
    del VERIFICATION_CODES[email]
    
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato.")
        
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/reset-password")
def reset_password(email: str = Form(...), new_password: str = Form(...), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email non trovata nel sistema.")
    
    user.hashed_password = get_password_hash(new_password)
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"message": "Password aggiornata con successo!"}

@app.put("/user/update-username")
def update_username(new_username: str = Form(...), current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.username == new_username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Questo nome utente è già in uso.")
    
    current_user.username = new_username
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return {"message": "Nome utente aggiornato con successo!"}

@app.get("/users/", response_model=list[dict])
def get_all_users(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    users = session.exec(select(User)).all()
    return [{"id": u.id, "username": u.username, "email": u.email} for u in users]

@app.get("/courses/", response_model=list[Course])
def read_courses(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    courses = session.exec(select(Course).where(Course.user_id == current_user.id)).all()
    return courses

@app.put("/courses/{course_id}/status")
def update_course_status(course_id: int, status: str = Form(...), current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    course = session.exec(select(Course).where(Course.id == course_id, Course.user_id == current_user.id)).first()
    if not course:
        raise HTTPException(status_code=404, detail="Corso non trovato.")
    
    course.status = status
    session.add(course)
    session.commit()
    session.refresh(course)
    return {"message": "Stato del corso aggiornato con successo!"}

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