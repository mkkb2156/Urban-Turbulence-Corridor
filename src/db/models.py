"""SQLAlchemy + GeoAlchemy2 資料庫模型。"""

from __future__ import annotations

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class GridCell(Base):
    """分析網格單元。"""

    __tablename__ = "grid_cells"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grid_id = Column(String(50), unique=True, nullable=False, index=True)
    city = Column(String(50), nullable=False, index=True)
    row = Column(Integer, nullable=False)
    col = Column(Integer, nullable=False)
    geometry = Column(Geometry("POLYGON", srid=3826), nullable=False)

    # 形態學指標
    bcr = Column(Float)
    svf = Column(Float)
    mean_height = Column(Float)
    max_height = Column(Float)
    n_buildings = Column(Integer)
    z0 = Column(Float)
    zd = Column(Float)

    # FAI（主要方向）
    fai_ne = Column(Float)  # 東北季風
    fai_sw = Column(Float)  # 西南季風
    fai_max = Column(Float)
    fai_max_direction = Column(Float)

    # 風速估算
    wind_50m = Column(Float)
    wind_80m = Column(Float)
    wind_120m = Column(Float)

    # 風廊
    is_corridor = Column(Boolean, default=False)
    corridor_rank = Column(Integer, default=-1)

    # 風險
    risk_level = Column(String(20))
    risk_score = Column(Float)

    # 中繼資料
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class WindCorridor(Base):
    """風廊路徑。"""

    __tablename__ = "wind_corridors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    corridor_id = Column(String(50), unique=True, nullable=False, index=True)
    city = Column(String(50), nullable=False, index=True)
    geometry = Column(Geometry("LINESTRING", srid=3826), nullable=False)
    corridor_class = Column(String(20))  # primary / secondary / minor
    total_cost = Column(Float)
    length_cells = Column(Integer)
    estimated_width = Column(Float)
    wind_direction = Column(String(20))  # northeast / southwest
    created_at = Column(DateTime, server_default=func.now())


class WeatherStation(Base):
    """氣象站。"""

    __tablename__ = "weather_stations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(String(20), unique=True, nullable=False, index=True)
    station_name = Column(String(100))
    geometry = Column(Geometry("POINT", srid=4326))
    city = Column(String(50), index=True)


class WindObservation(Base):
    """風場觀測紀錄。"""

    __tablename__ = "wind_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    station_id = Column(String(20), nullable=False, index=True)
    observation_time = Column(DateTime, nullable=False, index=True)
    wind_speed = Column(Float)  # m/s
    wind_direction = Column(Float)  # degrees
    gust_speed = Column(Float)  # m/s
