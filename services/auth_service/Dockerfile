FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir --default-timeout=300 -r requirements.txt

COPY . .

CMD ["python", "main.py"]