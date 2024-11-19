FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

ENV PORT=8080
ENV ENVIRONMENT=production
ENV DB=unilink-app-db-prod

EXPOSE $PORT
#
CMD exec fastapi run main.py --port ${PORT}
