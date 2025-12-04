import grpc
import json
import time
import sys
from typing import List, Optional, Union
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from datetime import datetime
from starlette.middleware.cors import CORSMiddleware
import os

# Add parent directory to path to find client module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# IMPORTANT: Import generated gRPC code and protobuf messages
from client import auth_pb2
from client import auth_pb2_grpc
from client import course_pb2
from client import course_pb2_grpc
from client import enrollment_pb2
from client import enrollment_pb2_grpc

# to run:
# uvicorn view_gateway:app --reload --port 8888

# CONFIG

REST_PORT = 8888 # The port the frontend (browser) will connect to
AUTH_SERVICE_ADDRESS = 'localhost:8000'
COURSE_SERVICE_ADDRESS = 'localhost:8001'
ENROLLMENT_SERVICE_ADDRESS = 'localhost:8002'

app = FastAPI(title="View Node / REST-to-gRPC Gateway")

# Allow CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from frontend directory
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

# Serve CSS and JS files directly
@app.get("/css/{file_path:path}")
async def serve_css(file_path: str):
    css_path = os.path.join(frontend_path, "css", file_path)
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    raise HTTPException(status_code=404)

@app.get("/js/{file_path:path}")
async def serve_js(file_path: str):
    js_path = os.path.join(frontend_path, "js", file_path)
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    raise HTTPException(status_code=404)

# --- gRPC Stub Initialization ---

# Helper function to get gRPC stubs
def get_auth_stub():
    channel = grpc.insecure_channel(AUTH_SERVICE_ADDRESS)
    return auth_pb2_grpc.AuthServiceStub(channel)

def get_course_stub():
    channel = grpc.insecure_channel(COURSE_SERVICE_ADDRESS)
    return course_pb2_grpc.CourseServiceStub(channel)

def get_enrollment_stub():
    channel = grpc.insecure_channel(ENROLLMENT_SERVICE_ADDRESS)
    return enrollment_pb2_grpc.EnrollmentServiceStub(channel)

# --- Utility Functions ---

def handle_grpc_error(e: grpc.RpcError):
    """Translates gRPC errors to appropriate HTTP exceptions."""
    details = e.details()
    code = e.code()
    
    if code == grpc.StatusCode.UNAUTHENTICATED:
        raise HTTPException(status_code=401, detail=details or "Invalid credentials or token.")
    elif code == grpc.StatusCode.NOT_FOUND:
        raise HTTPException(status_code=404, detail=details or "Resource not found.")
    elif code == grpc.StatusCode.ALREADY_EXISTS:
        raise HTTPException(status_code=409, detail=details or "Resource already exists.")
    elif code == grpc.StatusCode.RESOURCE_EXHAUSTED:
        raise HTTPException(status_code=429, detail=details or "Resource exhausted (e.g., course full).")
    elif code == grpc.StatusCode.UNAVAILABLE:
        raise HTTPException(status_code=503, detail=details or "Backend service is currently unavailable.")
    else:
        # Catch-all for other internal errors
        raise HTTPException(status_code=500, detail=f"Internal Service Error: {code.name} - {details}")

# --- Pydantic Schemas (REST Data Models) ---

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

class VerificationResult(BaseModel):
    valid: bool
    username: str
    role: str

class LogoutResponse(BaseModel):
    success: bool
    message: str

class CourseOut(BaseModel):
    id: int
    code: str
    title: str
    slots: int
    is_open: bool

class EnrollmentRequest(BaseModel):
    course_id: int

class EnrollmentResponse(BaseModel):
    success: bool
    message: str
    enrollment_id: int

class GradeRecordOut(BaseModel):
    enrollment_id: int
    course_id: int
    course_code: str
    course_title: str
    student_username: str
    grade: float = Field(default=0.0, description="Numerical grade, 0.0 to 4.0")
    status: str

class UploadGradeRequest(BaseModel):
    enrollment_id: int
    grade: float = Field(..., ge=0.0, le=4.0)


# --- Dependency: Token Verification and User Extraction ---

# NOTE: In a real-world system, this dependency would communicate with the Auth Service 
# to verify the token on every protected API call. For simplicity here, we assume
# the token is passed in the header and we will verify it with the gRPC service.
def verify_token_dependency(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Extracts and verifies the JWT token using the Auth gRPC Service."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required. No token provided.")
        
    token = authorization.split(" ")[1]
    
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required. Invalid token format.")
    
    auth_stub = get_auth_stub()
    try:
        verify_request = auth_pb2.VerifyTokenRequest(token=token)
        verify_response = auth_stub.VerifyToken(verify_request)
        
        if not verify_response.valid:
            raise HTTPException(status_code=401, detail="Invalid or expired token.")
        
        # Return user data for use in downstream endpoints
        return VerificationResult(
            valid=verify_response.valid,
            username=verify_response.username,
            role=verify_response.role
        )
    except grpc.RpcError as e:
        # Log the actual gRPC error for debugging
        if e.code() == grpc.StatusCode.UNAVAILABLE:
            raise HTTPException(status_code=503, detail=f"Auth Service unavailable: {e.details()}")
        handle_grpc_error(e)
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log unexpected errors
        import traceback
        print(f"Token verification error: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Token verification failed: {str(e)}")


# --- API ENDPOINTS (The REST Layer) ---

@app.get("/")
async def root():
    """Serve index.html or return health check."""
    frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"status": "View Node (REST Gateway) is running", "port": REST_PORT}

@app.get("/index.html")
async def serve_index():
    """Serve index.html."""
    frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="Index page not found")

@app.get("/dashboard.html")
async def serve_dashboard():
    """Serve dashboard.html."""
    frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    dashboard_path = os.path.join(frontend_path, "dashboard.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="Dashboard not found")

# --- 1. AUTH Endpoints ---

@app.post("/api/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Receives REST login request and calls Auth gRPC Service."""
    auth_stub = get_auth_stub()
    try:
        login_request = auth_pb2.LoginRequest(username=request.username, password=request.password)
        login_response = auth_stub.Login(login_request)
        
        if not login_response.access_token:
            raise HTTPException(status_code=401, detail="Login failed: No token received")
        
        return LoginResponse(
            access_token=login_response.access_token,
            role=login_response.role
        )
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.UNAVAILABLE:
            raise HTTPException(status_code=503, detail=f"Auth Service is not available. Make sure it's running on {AUTH_SERVICE_ADDRESS}")
        handle_grpc_error(e)

@app.get("/api/verify_auth", response_model=VerificationResult)
async def verify_auth(user: VerificationResult = Depends(verify_token_dependency)):
    """Verifies the token via the dependency and returns the user payload."""
    return user

@app.post("/api/logout", response_model=LogoutResponse)
async def logout(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Logs out the user by invalidating their JWT token."""
    # Extract token from Authorization header
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    token = authorization.split(" ")[1]
    
    auth_stub = get_auth_stub()
    try:
        logout_request = auth_pb2.LogoutRequest(token=token)
        logout_response = auth_stub.Logout(logout_request)
        
        return LogoutResponse(
            success=logout_response.success,
            message=logout_response.message
        )
    except grpc.RpcError as e:
        handle_grpc_error(e)


# --- 2. COURSE Endpoints (Requires Auth) ---

@app.get("/api/courses", response_model=List[CourseOut])
async def list_open_courses(user: VerificationResult = Depends(verify_token_dependency)):
    """Lists open courses by calling Course gRPC Service."""
    course_stub = get_course_stub()
    try:
        list_response = course_stub.ListCourses(course_pb2.ListCoursesRequest())
        
        # Convert gRPC Course message to Pydantic CourseOut model
        return [
            CourseOut(
                id=c.id, code=c.code, title=c.title, slots=c.slots, is_open=c.is_open
            ) for c in list_response.courses
        ]
    except grpc.RpcError as e:
        handle_grpc_error(e)


# --- 3. ENROLLMENT Endpoints (Requires Auth) ---

@app.post("/api/enroll", response_model=EnrollmentResponse)
async def enroll_student(
    request: EnrollmentRequest, 
    user: VerificationResult = Depends(verify_token_dependency)
):
    """Enrolls student by calling Enrollment gRPC Service."""
    
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can enroll in courses.")
        
    enroll_stub = get_enrollment_stub()
    try:
        enroll_request = enrollment_pb2.EnrollRequest(
            student_username=user.username,
            course_id=request.course_id
        )
        enroll_response = enroll_stub.Enroll(enroll_request)
        
        return EnrollmentResponse(
            success=enroll_response.success,
            message=enroll_response.message,
            enrollment_id=enroll_response.enrollment_id
        )
    except grpc.RpcError as e:
        handle_grpc_error(e)

@app.get("/api/grades", response_model=List[GradeRecordOut])
async def view_grades(user: VerificationResult = Depends(verify_token_dependency)):
    """Views student's grades by calling Enrollment gRPC Service."""
    
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can view their grades.")
        
    enroll_stub = get_enrollment_stub()
    try:
        view_request = enrollment_pb2.ViewGradesRequest(student_username=user.username)
        view_response = enroll_stub.ViewGrades(view_request)
        
        # Convert gRPC GradeRecord message to Pydantic GradeRecordOut model
        return [
            GradeRecordOut(
                enrollment_id=r.enrollment_id,
                course_id=r.course_id,
                course_code=r.course_code,
                course_title=r.course_title,
                student_username=r.student_username,
                grade=r.grade, # Float transfer is handled automatically
                status=r.status
            ) for r in view_response.records
        ]
    except grpc.RpcError as e:
        handle_grpc_error(e)


@app.post("/api/upload_grade", response_model=GradeRecordOut)
async def upload_grade(
    request: UploadGradeRequest,
    user: VerificationResult = Depends(verify_token_dependency)
):
    """Uploads a grade by calling Enrollment gRPC Service."""
    
    if user.role != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty can upload grades.")
        
    enroll_stub = get_enrollment_stub()
    try:
        upload_request = enrollment_pb2.UploadGradeRequest(
            faculty_username=user.username,
            enrollment_id=request.enrollment_id,
            grade=request.grade
        )
        upload_response = enroll_stub.UploadGrade(upload_request)
        
        if not upload_response.success:
            raise HTTPException(status_code=500, detail=upload_response.message)
        
        # Use the updated_record returned directly from the service
        if upload_response.updated_record:
            updated_record = upload_response.updated_record
            return GradeRecordOut(
                enrollment_id=updated_record.enrollment_id,
                course_id=updated_record.course_id,
                course_code=updated_record.course_code,
                course_title=updated_record.course_title,
                student_username=updated_record.student_username,
                grade=updated_record.grade,
                status=updated_record.status
            )
        
        raise HTTPException(status_code=500, detail="Grade uploaded but no record returned.")
        
    except grpc.RpcError as e:
        handle_grpc_error(e)