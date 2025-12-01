from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

# to run
# uvicorn course_service:app --reload --port 8001


# DATABASE SETUP
DATABASE_URL = "sqlite:///./courses.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    title = Column(String)
    slots = Column(Integer)
    is_open = Column(Boolean, default=True)

Base.metadata.create_all(bind=engine)


# FASTAPI APP
app = FastAPI(title="Course Service")


# SCHEMAS
class CourseCreate(BaseModel):
    code: str
    title: str
    slots: int

class CourseOut(BaseModel):
    id: int
    code: str
    title: str
    slots: int
    is_open: bool

    class Config:
        orm_mode = True


# API ENDPOINTS
@app.get("/")
def health_check():
    return {"status": "Course Service running"}

@app.get("/courses", response_model=List[CourseOut])
def list_courses():
    db = SessionLocal()
    courses = db.query(Course).filter(Course.is_open == True).all()
    db.close()
    return courses

@app.post("/courses", response_model=CourseOut)
def add_course(course: CourseCreate):
    db = SessionLocal()

    existing = db.query(Course).filter(Course.code == course.code).first()
    if existing:
        db.close()
        raise HTTPException(status_code=400, detail="Course already exists")

    new_course = Course(
        code=course.code,
        title=course.title,
        slots=course.slots,
        is_open=True
    )

    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    db.close()

    return new_course

@app.put("/courses/{course_id}/close")
def close_course(course_id: int):
    db = SessionLocal()
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        db.close()
        raise HTTPException(status_code=404, detail="Course not found")

    course.is_open = False
    db.commit()
    db.close()

    return {"message": "Course closed"}

@app.put("/courses/{course_id}/slots/{new_slots}")
def update_slots(course_id: int, new_slots: int):
    db = SessionLocal()
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        db.close()
        raise HTTPException(status_code=404, detail="Course not found")

    course.slots = new_slots
    db.commit()
    db.close()

    return {"message": "Slots updated"}
