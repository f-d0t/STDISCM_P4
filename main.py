import grpc
import time
from concurrent import futures
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError

# SQLAlchemy imports for database persistence
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# Import generated gRPC code
import auth_pb2
import auth_pb2_grpc

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


# DATABASE SETUP

DATABASE_URL = "sqlite:///./auth.db"

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
    expire = datetime.utcnow() + expires_delta
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
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Check if user still exists in the database
            username = payload.get("sub")
            role = payload.get("role")
            
            if not username or not role or not get_user_by_username(username):
                raise JWTError("User not found or missing claims.")

            return auth_pb2.VerifyTokenResponse(
                username=username,
                role=role,
                valid=True
            )
        except JWTError:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details("Invalid or expired token")
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


# --- gRPC Server Startup ---

def serve():
    """Starts the gRPC server for the Auth Service."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthServicer(), server)

    bind_address = f'[::]:{GRPC_PORT}'
    server.add_insecure_port(bind_address)
    print(f"Auth Service server (gRPC) starting on {bind_address}.")
    server.start()

    try:
        while True:
            time.sleep(86400) 
    except KeyboardInterrupt:
        print("Stopping Auth Service server...")
        server.stop(0)

if __name__ == '__main__':
    serve()