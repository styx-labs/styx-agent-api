FROM python:3.11-slim

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

ENV ENVIRONMENT=production
ENV DB=unilink-app-db-prod
ENV PORT=8080

# Use uvicorn to run the FastAPI app
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT