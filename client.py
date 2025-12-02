import grpc
import time
import random

# IMPORTANT: These imports rely on the generated gRPC files.
# Make sure you run the compilation command first!
import auth_pb2
import auth_pb2_grpc
import course_pb2
import course_pb2_grpc
import enrollment_pb2
import enrollment_pb2_grpc

# --- Service Addresses ---
AUTH_SERVICE_ADDRESS = 'localhost:8000'
COURSE_SERVICE_ADDRESS = 'localhost:8001'
ENROLLMENT_SERVICE_ADDRESS = 'localhost:8002'

# --- Helper Functions for gRPC Connection ---

def get_auth_stub():
    """Returns a gRPC stub for the Auth Service."""
    channel = grpc.insecure_channel(AUTH_SERVICE_ADDRESS)
    return auth_pb2_grpc.AuthServiceStub(channel)

def get_course_stub():
    """Returns a gRPC stub for the Course Service."""
    channel = grpc.insecure_channel(COURSE_SERVICE_ADDRESS)
    return course_pb2_grpc.CourseServiceStub(channel)

def get_enrollment_stub():
    """Returns a gRPC stub for the Enrollment Service."""
    channel = grpc.insecure_channel(ENROLLMENT_SERVICE_ADDRESS)
    return enrollment_pb2_grpc.EnrollmentServiceStub(channel)

# --- Test Functions ---

NEW_USER = f"newuser{random.randint(100, 999)}"
NEW_PASS = "securepassword"

def test_create_account(stub):
    """Tests the CreateAccount RPC."""
    print("--- 1. Testing CREATE ACCOUNT Feature ---")
    
    # Test 1.1: Successful Creation (Providing required role)
    print(f"[1.1] Attempting to create new user: {NEW_USER} as 'student'...")
    try:
        create_request = auth_pb2.CreateAccountRequest(
            username=NEW_USER,
            password=NEW_PASS,
            role="student" # Required field
        )
        create_response = stub.CreateAccount(create_request)
        if create_response.success:
            print(f"[1.1 SUCCESS] Account created. Role: {create_response.role}")
        else:
            print(f"[1.1 FAILED] Creation failed unexpectedly.")
    except grpc.RpcError as e:
        print(f"[1.1 FAILED] Creation failed: {e.code().name} - {e.details()}")
        return
        
    # Test 1.2: Failed Creation (Duplicate User)
    print(f"[1.2] Attempting to create duplicate user: {NEW_USER}...")
    try:
        duplicate_request = auth_pb2.CreateAccountRequest(
            username=NEW_USER,
            password=NEW_PASS,
            role="student"
        )
        stub.CreateAccount(duplicate_request)
        print("[1.2 FAILED] Did not raise expected ALREADY_EXISTS error.")
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.ALREADY_EXISTS:
            print(f"[1.2 SUCCESS] (Expected Failure) Code: {e.code().name} - {e.details()}")
        else:
             print(f"[1.2 FAILED] Failed with unexpected error: {e.code().name} - {e.details()}")
             
    # Test 1.3: Failed Creation (Invalid Role)
    INVALID_ROLE = "admin"
    print(f"[1.3] Attempting to create user with invalid role: '{INVALID_ROLE}'...")
    try:
        invalid_role_request = auth_pb2.CreateAccountRequest(
            username=f"baduser{random.randint(1,999)}",
            password="pwd",
            role=INVALID_ROLE
        )
        stub.CreateAccount(invalid_role_request)
        print("[1.3 FAILED] Did not raise expected INVALID_ARGUMENT error.")
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.INVALID_ARGUMENT:
            print(f"[1.3 SUCCESS] (Expected Failure) Code: {e.code().name} - {e.details()}")
        else:
             print(f"[1.3 FAILED] Failed with unexpected error: {e.code().name} - {e.details()}")
        
    
def test_auth_service(stub):
    """Tests Login and VerifyToken RPCs, including login for the new user."""
    print("\n--- 2. Testing AUTH Service (Login/Verify) ---")
    
    # Test 2.1: Login with new user
    token = None
    try:
        login_request = auth_pb2.LoginRequest(username=NEW_USER, password=NEW_PASS)
        login_response = stub.Login(login_request)
        token = login_response.access_token
        print(f"[2.1 SUCCESS] Logged in as {login_response.role} using new account. Token: {token[:20]}...")
    except grpc.RpcError as e:
        print(f"[2.1 FAILED] Login failed: {e.code().name} - {e.details()}")

    return token
    

# Remaining test functions remain the same for Course and Enrollment
def test_course_service(stub):
    """Tests AddCourse and ListCourses RPCs, and returns a reliable course ID."""
    print("\n--- 3. Testing COURSE Service (Node 8001) ---")
    course_id = None
    
    unique_code = f"TEST{random.randint(1000, 9999)}"

    # Test 3.1: Add a unique Course
    print(f"[3.1] Adding new course ({unique_code})...")
    try:
        add_request = course_pb2.AddCourseRequest(
            code=unique_code,
            title="Distributed Systems Test Course",
            slots=10
        )
        add_response = stub.AddCourse(add_request)
        course_id = add_response.course.id
        print(f"[3.1 SUCCESS] Added Course ID: {course_id}, Title: {add_response.course.title}")
    except grpc.RpcError as e:
        print(f"[3.1 FAILED] Could not add course: {e.code().name} - {e.details()}")
        return None
        
    # Test 3.2: List Courses
    print("[3.2] Listing available courses...")
    try:
        list_response = stub.ListCourses(course_pb2.ListCoursesRequest())
        course_codes = [c.code for c in list_response.courses]
        print(f"[3.2 SUCCESS] Found {len(list_response.courses)} course(s) open. {unique_code} in list: {unique_code in course_codes}")
    except grpc.RpcError as e:
        print(f"[3.2 FAILED] Could not list courses: {e.code().name} - {e.details()}")
        
    return course_id

def test_enrollment_service(enroll_stub, course_stub, reliable_course_id):
    """Tests Enrollment, Grade Upload, and View Grades RPCs."""
    print("\n--- 4. Testing ENROLLMENT Service (Node 8002) ---")
    enrollment_id = None
    
    # NOTE: We use the newly created user for enrollment test
    student_user = NEW_USER 
    faculty_user = "teacher1"
    
    if not reliable_course_id:
        print("[4.0 INFO] Skipping enrollment tests as no reliable course ID was found.")
        return

    # Test 4.1: Successful Enrollment (Involves inter-service call to Course Service)
    print(f"[4.1] Attempting enrollment for {student_user} in Course ID {reliable_course_id}...")
    try:
        enroll_request = enrollment_pb2.EnrollRequest(
            student_username=student_user,
            course_id=reliable_course_id
        )
        enroll_response = enroll_stub.Enroll(enroll_request)
        enrollment_id = enroll_response.enrollment_id
        print(f"[4.1 SUCCESS] {enroll_response.message}. Enrollment ID: {enrollment_id}")
    except grpc.RpcError as e:
        print(f"[4.1 FAILED] Enrollment failed: {e.code().name} - {e.details()}")
        return 

    # Test 4.2: Upload Grade (Faculty Action - Using 2.5)
    TEST_GRADE = 2.5
    print(f"[4.2] Uploading grade '{TEST_GRADE:.1f}' for Enrollment ID {enrollment_id}...")
    try:
        upload_request = enrollment_pb2.UploadGradeRequest(
            faculty_username=faculty_user,
            enrollment_id=enrollment_id,
            grade=TEST_GRADE
        )
        upload_response = enroll_stub.UploadGrade(upload_request)
        print(f"[4.2 SUCCESS] Grade uploaded: {upload_response.updated_grade:.1f}. {upload_response.message}")
    except grpc.RpcError as e:
        print(f"[4.2 FAILED] Upload Grade failed: {e.code().name} - {e.details()}")
        return

    # Test 4.3: View Grades (After Grade Upload - Should show 2.5)
    print(f"[4.3] Viewing grades for {student_user} (Post-grade)...")
    try:
        view_request = enrollment_pb2.ViewGradesRequest(student_username=student_user)
        view_response = enroll_stub.ViewGrades(view_request)
        record = next((r for r in view_response.records if r.enrollment_id == enrollment_id), None)
        if record and record.grade == TEST_GRADE:
            print(f"[4.3 SUCCESS] Grade updated to '{record.grade:.1f}'. Status: {record.status}")
        else:
            print(f"[4.3 FAILED] Grade was not updated correctly. Found grade: {record.grade}")
    except grpc.RpcError as e:
        print(f"[4.3 FAILED] View Grades failed: {e.code().name} - {e.details()}")


def run_tests():
    """Main function to orchestrate the testing across all three nodes."""
    print("===================================================================")
    print(">>> Starting gRPC Microservice Integration Tests (Role Required) <<<")
    print("-------------------------------------------------------------------")
    
    # 1. Initialize Stubs
    auth_stub = get_auth_stub()
    course_stub = get_course_stub()
    enroll_stub = get_enrollment_stub()
    
    # 2. Test Account Creation (NEW STEP)
    test_create_account(auth_stub)
    time.sleep(0.5) 
    
    # 3. Test Auth (Login using the new user)
    auth_token = test_auth_service(auth_stub)
    time.sleep(0.5) 
    
    # 4. Test Course Management and get a Course ID
    reliable_course_id = test_course_service(course_stub)
    time.sleep(0.5) 
    
    # 5. Test Enrollment and Grading (using the new user)
    test_enrollment_service(enroll_stub, course_stub, reliable_course_id)
    
    print("\n===================================================================")
    print(">>> All Microservice Integration Tests Complete <<<")
    print("===================================================================")

if __name__ == '__main__':
    run_tests()