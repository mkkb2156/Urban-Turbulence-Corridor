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

    # 衍生指標（Phase 3）
    turbulence_50m = Column(Float)
    turbulence_80m = Column(Float)
    turbulence_120m = Column(Float)
    shear_50_80 = Column(Float)
    shear_80_120 = Column(Float)
    gust_factor = Column(Float)
    shelter_index = Column(Float)
    min_safe_alt = Column(Float)
    max_legal_alt = Column(Float, default=120.0)
    wind_direction_deg = Column(Float)

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


class AirspaceZone(Base):
    """空域限制區。"""

    __tablename__ = "airspace_zones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    zone_id = Column(Text, unique=True, nullable=False)
    name = Column(Text, nullable=False)
    zone_type = Column(Text, nullable=False)  # prohibited / restricted / airport / military / special
    restriction = Column(Text)  # no_fly / height_limit / permit_required
    max_height_m = Column(Float)
    geometry = Column(Geometry("POLYGON", srid=3826), nullable=False)
    source = Column(Text, default="caa")
    valid_from = Column(DateTime)
    valid_until = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class FlightCondition(Base):
    """時序飛行條件。"""

    __tablename__ = "flight_conditions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grid_id = Column(Text, nullable=False, index=True)
    forecast_time = Column(DateTime, nullable=False, index=True)
    wind_speed_50m = Column(Float)
    wind_speed_80m = Column(Float)
    wind_speed_120m = Column(Float)
    wind_direction = Column(Float)
    gust_speed = Column(Float)
    risk_level = Column(Text)
    turbulence_intensity = Column(Float)
    source = Column(Text, default="open_meteo")
    created_at = Column(DateTime, server_default=func.now())


class TerrainElevation(Base):
    """地形高程。"""

    __tablename__ = "terrain_elevation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grid_id = Column(Text, unique=True, nullable=False)
    dem_elevation = Column(Float)  # 地面高程 (m, MSL)
    dsm_elevation = Column(Float)  # 含建物高程 (m, MSL)
    slope_deg = Column(Float)
    aspect_deg = Column(Float)
    source = Column(Text, default="copernicus_glo30")
