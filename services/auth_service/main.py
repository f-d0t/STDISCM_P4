import grpc
import time
import sys
import os
from concurrent import futures
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

# Add parent directory to path to find client module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# SQLAlchemy imports for database persistence
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# Import generated gRPC code
from client import auth_pb2
from client import auth_pb2_grpc

# Make sure to run the compilation command:
# python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. auth.proto course.proto
# to run each service:
# python [filename]

# CONFIG & JWT SETUP

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
GRPC_PORT = "8000"

# Define allowed roles for validation
ALLOWED_ROLES = ["student", "faculty"]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- TOKEN BLACKLIST (for logout functionality) ---
# In-memory set to store blacklisted tokens
# For distributed systems, this should be in a shared cache (Redis) or database
# For this exercise, in-memory is sufficient within a single auth service node
_token_blacklist = set()


# DATABASE SETUP

DATABASE_URL = "sqlite:///./services/auth_service/auth.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}) 
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# --- Database Model ---
class User(Base):
    """SQLAlchemy model for storing persistent user data."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="student") 

Base.metadata.create_all(bind=engine)

# --- UTILITY FUNCTIONS ---
def verify_password(plain, hashed):
    """Verifies a plain text password against a hashed one."""
    return pwd_context.verify(plain, hashed)

def get_user_by_username(username: str):
    """Fetches a user from the database by username."""
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    return user

def create_user_in_db(username: str, password: str, role: str):
    """Creates a new user in the database."""
    db = SessionLocal()
    
    if db.query(User).filter(User.username == username).first():
        db.close()
        return None 

    hashed_password = pwd_context.hash(password)
    new_user = User(username=username, hashed_password=hashed_password, role=role)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.close()
    return new_user

def authenticate_user(username, password):
    """Authenticates a user by checking password against the database."""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    
    return {"username": user.username, "role": user.role}

def create_access_token(data: dict, expires_delta: timedelta):
    """Creates a signed JWT token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": int(expire.timestamp())})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- Initialization: Create Default Users if DB is Empty ---
def initialize_users():
    """Ensures default accounts ('student1', 'teacher1') exist."""
    db = SessionLocal()
    if db.query(User).count() == 0:
        print("Initializing default users...")
        create_user_in_db("student1", "password123", "student")
        create_user_in_db("teacher1", "password123", "faculty")
        print("Default users created: student1, teacher1.")
    db.close()

# Run initialization immediately
initialize_users()



# gRPC SERVICER IMPLEMENTATION


class AuthServicer(auth_pb2_grpc.AuthServiceServicer):
    """Implements the Auth Service defined in auth.proto."""
    
    def Login(self, request, context):
        """Handles user login and returns a JWT token."""
        user = authenticate_user(request.username, request.password)
        
        if not user:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details("Invalid credentials")
            return auth_pb2.LoginResponse()
            
        access_token = create_access_token(
            data={"sub": user["username"], "role": user["role"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        return auth_pb2.LoginResponse(
            access_token=access_token,
            role=user["role"]
        )

    def VerifyToken(self, request, context):
        """Verifies a JWT token and returns the user payload."""
        token = request.token
        
        if not token:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details("No token provided")
            return auth_pb2.VerifyTokenResponse(valid=False)
        
        # Check if token is blacklisted (logged out)
        if token in _token_blacklist:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details("Token has been invalidated (logged out)")
            return auth_pb2.VerifyTokenResponse(valid=False)
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Check if user still exists in the database
            username = payload.get("sub")
            role = payload.get("role")
            
            if not username or not role:
                print(f"VerifyToken: Missing claims - username: {username}, role: {role}")
                raise JWTError("Missing username or role in token")
            
            user = get_user_by_username(username)
            if not user:
                print(f"VerifyToken: User not found in database - username: {username}")
                raise JWTError("User not found in database")

            return auth_pb2.VerifyTokenResponse(
                username=username,
                role=role,
                valid=True
            )
        except JWTError as e:
            print(f"VerifyToken: JWTError - {str(e)}")
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details(f"Invalid or expired token: {str(e)}")
            return auth_pb2.VerifyTokenResponse(valid=False)
        except Exception as e:
            print(f"VerifyToken: Unexpected error - {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Token verification error: {str(e)}")
            return auth_pb2.VerifyTokenResponse(valid=False)

    def CreateAccount(self, request, context):
        """Handles new user registration."""
        
        # 1. Server-side validation for required role field
        if not request.role or request.role not in ALLOWED_ROLES:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(f"Invalid or missing role. Must be one of: {', '.join(ALLOWED_ROLES)}")
            return auth_pb2.CreateAccountResponse(success=False)

        # 2. Check for existing user
        if get_user_by_username(request.username):
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details(f"User '{request.username}' already exists.")
            return auth_pb2.CreateAccountResponse(success=False)
            
        # 3. Create user in DB
        # The role is now guaranteed to be valid and present due to steps 1 and 2
        new_user = create_user_in_db(request.username, request.password, request.role)
        
        if new_user:
            return auth_pb2.CreateAccountResponse(
                success=True,
                message=f"Account created successfully for {new_user.role}.",
                role=new_user.role
            )
        else:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Failed to create user in database.")
            return auth_pb2.CreateAccountResponse(success=False)

    def Logout(self, request, context):
        """Invalidates a JWT token by adding it to the blacklist."""
        token = request.token
        
        # Verify the token first to ensure it's valid before blacklisting
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            # Token is valid, add it to blacklist
            _token_blacklist.add(token)
            
            # Optional: Clean up expired tokens from blacklist periodically
            # For now, we'll let them accumulate (they're just strings)
            # In production, implement TTL cleanup or use Redis with expiration
            
            return auth_pb2.LogoutResponse(
                success=True,
                message="Successfully logged out. Token has been invalidated."
            )
        except JWTError:
            # Token is already invalid/expired, but we'll still return success
            # to not reveal information about token validity
            return auth_pb2.LogoutResponse(
                success=True,
                message="Logout completed."
            )


# --- gRPC Server Startup ---

def serve():
    """Starts the gRPC server for the Auth Service."""
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthServicer(), server)

        bind_address = f'[::]:{GRPC_PORT}'
        server.add_insecure_port(bind_address)
        print(f"Auth Service server (gRPC) starting on {bind_address}.")
        server.start()
        print(f"✓ Auth Service is running and ready to accept requests on port {GRPC_PORT}")

        try:
            while True:
                time.sleep(86400) 
        except KeyboardInterrupt:
            print("\nStopping Auth Service server...")
            server.stop(0)
    except Exception as e:
        print(f"✗ Error starting Auth Service: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    serve()