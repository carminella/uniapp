from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List

# --- MODELLO UTENTE ---
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str

    # Relazioni: un utente ha i suoi corsi
    courses: List["Course"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


# --- MODELLO CORSO ---
class Course(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    status: str = "in studio"  # "in studio" o "completato"
    
    # Chiave esterna per associare il corso all'utente proprietario
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    user: Optional[User] = Relationship(back_populates="courses")

    # Relazione con gli appunti
    notes: List["Note"] = Relationship(back_populates="course", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


# --- MODELLO APPUNTO ---
class Note(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    file_path: str
    difficulty_level: int = 1
    
    # Chiave esterna per associare l'appunto al corso
    course_id: Optional[int] = Field(default=None, foreign_key="course.id")
    course: Optional[Course] = Relationship(back_populates="notes")