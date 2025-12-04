import grpc
import time
import sys
import os
from concurrent import futures
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import IntegrityError

# Add parent directory to path to find client module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# IMPORTANT: These imports rely on the generated gRPC files.
# Make sure you run the compilation command:
# python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. auth.proto course.proto
from client import course_pb2
from client import course_pb2_grpc



# DATABASE SETUP

DATABASE_URL = "sqlite:///./services/course_service/courses.db"
GRPC_PORT = "8001" # This node runs on port 8001

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

# --- gRPC Servicer Implementation ---

# The CourseServicer must inherit from the generated ServiceBase class
class CourseServicer(course_pb2_grpc.CourseServiceServicer):
    """Implements the Course Service defined in course.proto."""

    def ListCourses(self, request, context):
        """Lists all open courses."""
        db = SessionLocal()
        try:
            # Filter for open courses
            courses_db = db.query(Course).filter(Course.is_open == True).all()
            
            # Map SQLAlchemy objects to gRPC Course message objects
            courses_grpc = [
                course_pb2.Course(
                    id=c.id,
                    code=c.code,
                    title=c.title,
                    slots=c.slots,
                    is_open=c.is_open
                ) for c in courses_db
            ]
            
            # Return the structured gRPC response
            return course_pb2.ListCoursesResponse(courses=courses_grpc)
        finally:
            db.close()


    def AddCourse(self, request, context):
        """Adds a new course to the database."""
        db = SessionLocal()
        try:
            # Check for existing course code before attempting to add
            existing = db.query(Course).filter(Course.code == request.code).first()
            if existing:
                context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                context.set_details("Course with this code already exists")
                return course_pb2.AddCourseResponse()

            new_course = Course(
                code=request.code,
                title=request.title,
                slots=request.slots,
                is_open=True
            )

            db.add(new_course)
            db.commit()
            db.refresh(new_course)

            # Return the new course as a gRPC Course message
            return course_pb2.AddCourseResponse(
                course=course_pb2.Course(
                    id=new_course.id,
                    code=new_course.code,
                    title=new_course.title,
                    slots=new_course.slots,
                    is_open=new_course.is_open
                )
            )
        finally:
            db.close()

    def CloseCourse(self, request, context):
        """Closes a course, setting is_open to False."""
        db = SessionLocal()
        try:
            course = db.query(Course).filter(Course.id == request.course_id).first()

            if not course:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Course ID {request.course_id} not found")
                return course_pb2.OperationResponse(success=False)

            course.is_open = False
            db.commit()

            return course_pb2.OperationResponse(
                success=True,
                message=f"Course ID {request.course_id} closed successfully."
            )
        finally:
            db.close()

    def UpdateSlots(self, request, context):
        """Updates the number of available slots for a course."""
        db = SessionLocal()
        try:
            course = db.query(Course).filter(Course.id == request.course_id).first()

            if not course:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Course ID {request.course_id} not found")
                return course_pb2.OperationResponse(success=False)

            if request.new_slots < 0:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Slots cannot be negative")
                return course_pb2.OperationResponse(success=False)

            course.slots = request.new_slots
            db.commit()

            return course_pb2.OperationResponse(
                success=True,
                message=f"Slots for Course ID {request.course_id} updated to {request.new_slots}."
            )
        finally:
            db.close()

# --- gRPC Server Startup ---

def serve():
    """Starts the gRPC server for the Course Service."""
    # Use a ThreadPoolExecutor to handle concurrent requests
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Add the implemented servicer to the server
    course_pb2_grpc.add_CourseServiceServicer_to_server(CourseServicer(), server)

    bind_address = f'[::]:{GRPC_PORT}'
    server.add_insecure_port(bind_address)
    print(f"Course Service server starting on {bind_address}")
    server.start()

    try:
        # Keep the main thread alive for the server
        while True:
            time.sleep(86400) # Sleep for a long time
    except KeyboardInterrupt:
        print("Stopping Course Service server...")
        server.stop(0)

if __name__ == '__main__':
    serve()