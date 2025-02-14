import uuid

from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

Base = declarative_base()

# sqlite db
class PodcastDB(Base):
    __tablename__ = "podcasts"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    # Mark other fields as nullable so they can be empty initially
    description = Column(String, nullable=True)
    chapters = Column(String, nullable=True)
    transcript = Column(JSON, nullable=True)
    voice_names = Column(JSON, nullable=True)
    settings = Column(JSON, nullable=True)