"""
Quick script to add test courses to the Course Service.
Run this after Course Service is running.
"""
import grpc
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from client import course_pb2, course_pb2_grpc

def add_test_courses():
    """Add sample courses for testing."""
    channel = grpc.insecure_channel('localhost:8001')
    stub = course_pb2_grpc.CourseServiceStub(channel)
    
    courses = [
        {"code": "CS101", "title": "Introduction to Computer Science", "slots": 30},
        {"code": "CS201", "title": "Data Structures and Algorithms", "slots": 25},
        {"code": "MATH101", "title": "Calculus I", "slots": 40},
        {"code": "PHYS101", "title": "Physics I", "slots": 35},
        {"code": "ENG101", "title": "English Composition", "slots": 20},
    ]
    
    print("Adding test courses...")
    for course_data in courses:
        try:
            response = stub.AddCourse(course_pb2.AddCourseRequest(
                code=course_data["code"],
                title=course_data["title"],
                slots=course_data["slots"]
            ))
            print(f"✓ Added: {course_data['code']} - {course_data['title']} ({course_data['slots']} slots)")
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.ALREADY_EXISTS:
                print(f"⚠ {course_data['code']} already exists, skipping...")
            else:
                print(f"✗ Error adding {course_data['code']}: {e.details()}")
    
    print("\nDone! You can now test enrollment in the frontend.")

if __name__ == "__main__":
    add_test_courses()

