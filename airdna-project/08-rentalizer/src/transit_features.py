"""Transit proximity features using NYC subway station data."""
import os
import logging
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

logger = logging.getLogger(__name__)

MTA_STATIONS_URL = "https://data.cityofnewyork.us/api/views/kk4q-3rt2/rows.csv"
STATIONS_CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "mta_stations.csv")


class TransitFeatureBuilder:
    """Compute transit proximity features for NYC listings."""

    def __init__(self):
        self.stations = self._load_stations()
        self.tree = None
        self._build_tree()

    def _load_stations(self) -> pd.DataFrame:
        """Load NYC subway station data."""
        if os.path.exists(STATIONS_CACHE):
            logger.info(f"Loading cached stations from {STATIONS_CACHE}")
            return pd.read_csv(STATIONS_CACHE)

        logger.info("Downloading MTA station data...")
        try:
            df = pd.read_csv(MTA_STATIONS_URL)
            # Normalize column names
            col_map = {}
            for col in df.columns:
                col_lower = col.lower().strip()
                if "station" in col_lower and "name" in col_lower:
                    col_map[col] = "name"
                elif col_lower == "latitude":
                    col_map[col] = "lat"
                elif col_lower == "longitude":
                    col_map[col] = "lng"
                elif col_lower == "line":
                    col_map[col] = "line"
                elif col_lower == "borough":
                    col_map[col] = "borough"
            df = df.rename(columns=col_map)

            if "lat" not in df.columns or "lng" not in df.columns:
                # Try alternate column names
                for col in df.columns:
                    if "lat" in col.lower():
                        df = df.rename(columns={col: "lat"})
                    if "lon" in col.lower() or "lng" in col.lower():
                        df = df.rename(columns={col: "lng"})

            df = df.dropna(subset=["lat", "lng"])
            df.to_csv(STATIONS_CACHE, index=False)
            logger.info(f"Cached {len(df)} stations")
            return df
        except Exception as e:
            logger.warning(f"Failed to load MTA stations: {e}")
            return pd.DataFrame(columns=["name", "lat", "lng", "line", "borough"])

    def _build_tree(self):
        """Build KD-Tree for fast nearest-station lookup."""
        if len(self.stations) == 0:
            return
        coords = self.stations[["lat", "lng"]].values
        # Convert to approximate meters for NYC (1 deg lat ≈ 111km, 1 deg lng ≈ 85km)
        self.coords_m = np.column_stack([coords[:, 0] * 111_000, coords[:, 1] * 85_000])
        self.tree = cKDTree(self.coords_m)

    def compute_features(self, lat: float, lng: float) -> dict:
        """For a single listing, compute transit features."""
        if self.tree is None or len(self.stations) == 0:
            return {
                "dist_to_subway_km": 1.0,
                "subway_within_200m": 0,
                "subway_within_400m": 0,
                "transit_density_1km": 0,
            }

        point_m = np.array([lat * 111_000, lng * 85_000])
        dist, idx = self.tree.query(point_m, k=1)
        dist_km = float(dist / 1000)

        # Count stations within 1km
        dists, _ = self.tree.query(point_m, k=min(20, len(self.stations)))
        density = int(np.sum(dists < 1000))

        return {
            "dist_to_subway_km": round(dist_km, 3),
            "subway_within_200m": int(dist < 200),
            "subway_within_400m": int(dist < 400),
            "transit_density_1km": density,
        }
