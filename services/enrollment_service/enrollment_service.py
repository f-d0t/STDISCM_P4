import grpc
import time
import sys
import os
from concurrent import futures
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float # Import Float
from sqlalchemy.orm import declarative_base, sessionmaker

# Add parent directory to path to find client module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import generated gRPC code
from client import enrollment_pb2
from client import enrollment_pb2_grpc
# Import Course gRPC client necessities for inter-service communication
from client import course_pb2
from client import course_pb2_grpc 


# CONFIG

DATABASE_URL = "sqlite:///./services/enrollment_service/enrollment.db"
GRPC_PORT = "8002" # This node runs on port 8002
COURSE_SERVICE_ADDRESS = 'localhost:8001' # Address of the Course Node

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# --- Database Models ---

class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    student_username = Column(String, index=True)
    course_id = Column(Integer, index=True) # ID from the Course Service's DB
    grade = Column(Float, nullable=True)   
    status = Column(String, default="ENROLLED") # ENROLLED, COMPLETED, DROPPED

Base.metadata.create_all(bind=engine)

# --- gRPC Inter-Service Client Helper ---

def get_course_stub():
    """Returns a gRPC stub for the Course Service."""
    channel = grpc.insecure_channel(COURSE_SERVICE_ADDRESS)
    return course_pb2_grpc.CourseServiceStub(channel)

# --- gRPC Servicer Implementation ---

class EnrollmentServicer(enrollment_pb2_grpc.EnrollmentServiceServicer):
    """Implements the Enrollment Service defined in enrollment.proto."""

    def Enroll(self, request, context):
        """Handles student enrollment, checks course availability via Course Service."""
        db = SessionLocal()
        course_stub = get_course_stub()
        
        try:
            # 1. Check if student is already enrolled
            existing = db.query(Enrollment).filter(
                Enrollment.student_username == request.student_username,
                Enrollment.course_id == request.course_id,
                Enrollment.status == "ENROLLED"
            ).first()
            
            if existing:
                context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                context.set_details("Student is already enrolled in this course.")
                return enrollment_pb2.EnrollResponse(success=False)

            # 2. Call Course Service to check course details and attempt slot update
            try:
                # We need to list all courses to find the course details (e.g., current slots)
                list_request = course_pb2.ListCoursesRequest()
                # Assuming the Course Service is available, otherwise this raises RpcError
                list_response = course_stub.ListCourses(list_request) 
                
                course_details = next((c for c in list_response.courses if c.id == request.course_id), None)
                
                if not course_details:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Course ID {request.course_id} not found or is closed.")
                    return enrollment_pb2.EnrollResponse(success=False)
                
                if course_details.slots <= 0:
                    context.set_code(grpc.StatusCode.RESOURCE_EXHAUSTED)
                    context.set_details("Course is full.")
                    return enrollment_pb2.EnrollResponse(success=False)

                # Attempt to reserve a slot by calling UpdateSlots on the Course Service
                new_slots = course_details.slots - 1
                update_request = course_pb2.UpdateSlotsRequest(
                    course_id=request.course_id,
                    new_slots=new_slots
                )
                update_response = course_stub.UpdateSlots(update_request)
                
                if not update_response.success:
                    context.set_code(grpc.StatusCode.ABORTED)
                    context.set_details(f"Enrollment failed due to slot update error: {update_response.message}")
                    return enrollment_pb2.EnrollResponse(success=False)

            except grpc.RpcError as e:
                # Handle failure in inter-service communication
                context.set_code(grpc.StatusCode.UNAVAILABLE)
                context.set_details(f"Course Service is unavailable or returned an error: {e.details()}")
                return enrollment_pb2.EnrollResponse(success=False)


            # 3. Create Enrollment Record
            new_enrollment = Enrollment(
                student_username=request.student_username,
                course_id=request.course_id,
                status="ENROLLED"
            )
            db.add(new_enrollment)
            db.commit()
            db.refresh(new_enrollment)

            return enrollment_pb2.EnrollResponse(
                success=True,
                message=f"Successfully enrolled in Course ID {request.course_id}. Slots remaining: {new_slots}",
                enrollment_id=new_enrollment.id
            )

        finally:
            db.close()


    def ViewGrades(self, request, context):
        """Allows students to view their enrollment records and grades."""
        db = SessionLocal()
        course_stub = get_course_stub()
        
        try:
            # 1. Get all enrollments for the student
            enrollments = db.query(Enrollment).filter(
                Enrollment.student_username == request.student_username
            ).all()

            if not enrollments:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("No enrollment records found for this student.")
                return enrollment_pb2.ViewGradesResponse()

            # 2. Get Course details from Course Service
            list_response = course_stub.ListCourses(course_pb2.ListCoursesRequest())
            course_map = {c.id: c for c in list_response.courses}

            records = []
            for e in enrollments:
                course_data = course_map.get(e.course_id)
                
                # Check if grade is present (not None) before passing to gRPC message
                grade_value = e.grade if e.grade is not None else 0.0

                records.append(
                    enrollment_pb2.GradeRecord(
                        enrollment_id=e.id,
                        course_id=e.course_id,
                        course_code=course_data.code if course_data else "UNKNOWN",
                        course_title=course_data.title if course_data else "UNKNOWN COURSE",
                        student_username=e.student_username,
                        grade=grade_value, 
                        status=e.status
                    )
                )

            return enrollment_pb2.ViewGradesResponse(records=records)

        except grpc.RpcError as e:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details(f"Course Service is unavailable or returned an error: {e.details()}")
            return enrollment_pb2.ViewGradesResponse()
        finally:
            db.close()


    def UploadGrade(self, request, context):
        """Allows faculty to upload a grade for a specific enrollment record."""
        db = SessionLocal()
        try:
            enrollment = db.query(Enrollment).filter(
                Enrollment.id == request.enrollment_id
            ).first()

            if not enrollment:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Enrollment ID {request.enrollment_id} not found.")
                return enrollment_pb2.UploadGradeResponse(success=False)
                
            # Basic validation for grade range
            if not (0.0 <= request.grade <= 4.0):
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Grade must be between 0.0 and 4.0.")
                return enrollment_pb2.UploadGradeResponse(success=False)


            # Update grade and set status to completed
            enrollment.grade = request.grade
            enrollment.status = "COMPLETED"
            db.commit()
            
            # Get course details for the full record
            course_stub = get_course_stub()
            try:
                list_response = course_stub.ListCourses(course_pb2.ListCoursesRequest())
                course_map = {c.id: c for c in list_response.courses}
                course_data = course_map.get(enrollment.course_id)
                
                # Build the full GradeRecord
                grade_record = enrollment_pb2.GradeRecord(
                    enrollment_id=enrollment.id,
                    course_id=enrollment.course_id,
                    course_code=course_data.code if course_data else "UNKNOWN",
                    course_title=course_data.title if course_data else "UNKNOWN COURSE",
                    student_username=enrollment.student_username,
                    grade=enrollment.grade,
                    status=enrollment.status
                )
                
                return enrollment_pb2.UploadGradeResponse(
                    success=True,
                    message=f"Grade '{request.grade}' uploaded successfully for Enrollment ID {request.enrollment_id}.",
                    updated_grade=enrollment.grade,
                    updated_record=grade_record
                )
            except grpc.RpcError:
                # If course service unavailable, return response without course details
                grade_record = enrollment_pb2.GradeRecord(
                    enrollment_id=enrollment.id,
                    course_id=enrollment.course_id,
                    course_code="UNKNOWN",
                    course_title="UNKNOWN COURSE",
                    student_username=enrollment.student_username,
                    grade=enrollment.grade,
                    status=enrollment.status
                )
                return enrollment_pb2.UploadGradeResponse(
                    success=True,
                    message=f"Grade '{request.grade}' uploaded successfully for Enrollment ID {request.enrollment_id}.",
                    updated_grade=enrollment.grade,
                    updated_record=grade_record
                )

        finally:
            db.close()

# --- gRPC Server Startup ---

def serve():
    """Starts the gRPC server for the Enrollment Service."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    enrollment_pb2_grpc.add_EnrollmentServiceServicer_to_server(EnrollmentServicer(), server)

    bind_address = f'[::]:{GRPC_PORT}'
    server.add_insecure_port(bind_address)
    print(f"Enrollment Service server starting on {bind_address}. DEPENDS on Course Service ({COURSE_SERVICE_ADDRESS})")
    server.start()

    try:
        while True:
            time.sleep(86400) 
    except KeyboardInterrupt:
        print("Stopping Enrollment Service server...")
        server.stop(0)

if __name__ == '__main__':
    print("Ensure all .proto files are compiled and Course Service (8001) is running!")
    serve()