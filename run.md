1) python compile_proto.py

2) python services/auth_service/main.py

3) python services/course_service/course_service.py

4) python services/enrollment_service/enrollment_service.py

5) cd gateway
   uvicorn view_gateway:app --reload --port 8888

6) http://localhost:8888/