FROM python:3.11-slim

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

ENV ENVIRONMENT=production
ENV DB=unilink-app-db-prod

ENV PORT=8080
EXPOSE ${PORT}
#
CMD exec fastapi run main.py --port ${PORT}
