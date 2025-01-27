FROM python:3.11-slim

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

ENV ENVIRONMENT=production
ENV DEVELOPMENT_MODE=false
ENV DB=styx-db-prod
ENV EVAL_ENDPOINT=https://styx-evaluate-16250094868.us-central1.run.app/evaluate
ENV SEARCH_ENDPOINT=https://styx-search-16250094868.us-central1.run.app/search
ENV PROJECT_ID=16250094868

ENV PORT=8080
EXPOSE ${PORT}
#
CMD exec fastapi run main.py --port ${PORT}
