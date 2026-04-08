FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir dash plotly requests

COPY . .

EXPOSE 8050

CMD ["python", "main.py"]