"""Quick test to verify Auth Service is running and can verify tokens."""
import grpc
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from client import auth_pb2, auth_pb2_grpc

def test_auth_service():
    """Test if Auth Service is accessible."""
    print("Testing Auth Service connection...")
    
    try:
        channel = grpc.insecure_channel('localhost:8000')
        stub = auth_pb2_grpc.AuthServiceStub(channel)
        
        # Test login
        print("\n1. Testing login...")
        login_response = stub.Login(auth_pb2.LoginRequest(
            username="student1",
            password="password123"
        ))
        
        if login_response.access_token:
            print(f"✓ Login successful! Token: {login_response.access_token[:30]}...")
            
            # Test token verification
            print("\n2. Testing token verification...")
            verify_response = stub.VerifyToken(auth_pb2.VerifyTokenRequest(
                token=login_response.access_token
            ))
            
            if verify_response.valid:
                print(f"✓ Token verification successful!")
                print(f"  Username: {verify_response.username}")
                print(f"  Role: {verify_response.role}")
            else:
                print("✗ Token verification failed - token marked as invalid")
        else:
            print("✗ Login failed - no token received")
            
    except grpc.RpcError as e:
        print(f"✗ gRPC Error: {e.code()} - {e.details()}")
        if e.code() == grpc.StatusCode.UNAVAILABLE:
            print("\n⚠ Auth Service is not running or not accessible on localhost:8000")
            print("   Make sure you started it with: python services/auth_service/main.py")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_auth_service()

