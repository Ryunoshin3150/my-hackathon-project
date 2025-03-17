FROM python:3.9.21
WORKDIR /app
COPY app/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt --no-cache-dir --upgrade
COPY app /app

CMD ["python3","/app/app.py", "port=8080"]
