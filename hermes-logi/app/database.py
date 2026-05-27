from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

DB_PATH = os.environ.get("DB_PATH", "hermes.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class ActualRecord(Base):
    __tablename__ = "actuals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site = Column(String, nullable=False)
    line = Column(String, nullable=False)
    floor = Column(String, nullable=False)
    dr_type = Column(String, nullable=False)
    actual_month = Column(String, nullable=False)  # YYYY-MM
    movement_actual = Column(Float)
    transport_count_actual = Column(Float)
    transport_time_actual = Column(Float)
    storage_product_actual = Column(Float)
    storage_total_actual = Column(Float)
    input_plan = Column(Float)  # history only
    created_at = Column(DateTime, default=datetime.utcnow)


class PlanRecord(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site = Column(String, nullable=False)
    line = Column(String, nullable=False)
    floor = Column(String, nullable=False)
    dr_type = Column(String, nullable=False)
    plan_month = Column(String, nullable=False)  # YYYY-MM
    movement_plan = Column(Float)
    wip_plan = Column(Float)
    lot_size = Column(Float)
    npw_plan = Column(Float)
    input_plan = Column(Float)  # stored for history
    created_at = Column(DateTime, default=datetime.utcnow)


class FloorConfig(Base):
    __tablename__ = "floor_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site = Column(String, nullable=False)
    floor = Column(String, nullable=False)
    line = Column(String, nullable=False)
    oht_count = Column(Integer, nullable=False)
    oht_monthly_hours = Column(Float, nullable=False)  # per unit


class StorageConfig(Base):
    __tablename__ = "storage_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site = Column(String, nullable=False)
    line = Column(String, nullable=False)
    floor = Column(String, nullable=False)
    storage_capacity = Column(Integer, nullable=False)


class DRStepConfig(Base):
    __tablename__ = "dr_step_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dr_type = Column(String, nullable=False, unique=True)
    step_count = Column(Integer, nullable=False)


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
