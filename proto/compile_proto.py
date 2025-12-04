#!/usr/bin/env python3
"""
Compile proto files and generate Python code in client/ directory.
This script ensures all generated files go to the correct location.
"""
import subprocess
import sys
import os

def compile_proto():
    """Compile all proto files to client/ directory."""
    
    proto_files = [
        "./auth.proto",
        "./course.proto",
        "./enrollment.proto"
    ]
    
    # Ensure proto files exist
    for proto_file in proto_files:
        if not os.path.exists(proto_file):
            print(f"Error: {proto_file} not found!")
            return False
    
    # Compile command
    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        "-I.",  # Include directory for proto imports
        "--python_out=client",  # Output directory for Python files
        "--pyi_out=client",  # Output directory for type stubs
        "--grpc_python_out=client",  # Output directory for gRPC files
    ] + proto_files
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Fix imports in generated _grpc.py files to use relative imports
        grpc_files = [
            "client/auth_pb2_grpc.py",
            "client/course_pb2_grpc.py",
            "client/enrollment_pb2_grpc.py"
        ]
        
        import_replacements = {
            "client/auth_pb2_grpc.py": ("import auth_pb2 as auth__pb2", "from . import auth_pb2 as auth__pb2"),
            "client/course_pb2_grpc.py": ("import course_pb2 as course__pb2", "from . import course_pb2 as course__pb2"),
            "client/enrollment_pb2_grpc.py": ("import enrollment_pb2 as enrollment__pb2", "from . import enrollment_pb2 as enrollment__pb2"),
        }
        
        for grpc_file in grpc_files:
            if os.path.exists(grpc_file):
                with open(grpc_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                old_import, new_import = import_replacements[grpc_file]
                if old_import in content and new_import not in content:
                    content = content.replace(old_import, new_import)
                    with open(grpc_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"✓ Fixed imports in {grpc_file}")
        
        print("✓ Proto files compiled successfully!")
        print("✓ Generated files are in client/ directory.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error compiling proto files: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Error: grpc_tools not found. Install it with:")
        print("  pip install grpcio-tools")
        return False

if __name__ == "__main__":
    success = compile_proto()
    sys.exit(0 if success else 1)

