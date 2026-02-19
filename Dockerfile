FROM python:3.10-slim
WORKDIR /code
COPY . .
RUN pip install aiogram httpx
CMD ["python", "main.py"]
