from sqlalchemy import Column, Integer, String, Text
from database import Base

class JobAnalysis(Base):
    __tablename__ = "job_analyses"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text)
    result = Column(Text)