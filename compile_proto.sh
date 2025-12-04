#!/bin/bash
# Compile proto files and generate Python code in client/ directory

python -m grpc_tools.protoc \
    -Iproto \
    --python_out=client \
    --pyi_out=client \
    --grpc_python_out=client \
    proto/auth.proto \
    proto/course.proto \
    proto/enrollment.proto

echo "Proto files compiled successfully! Generated files are in client/ directory."

