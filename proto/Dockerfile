FROM python:3.10-slim
WORKDIR /app
COPY compile_proto.py .
COPY *.proto /app/             
RUN pip install grpcio grpcio-tools
CMD ["python", "compile_proto.py"]