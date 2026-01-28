# Knowledge Graph + GIS Integration

## Geospatial Intelligence for Community Resilience

---

## Executive Summary

The combination of **Knowledge Graph + GIS + LLM** creates a powerful system where:

1. **The Knowledge Graph** provides structured relationships and attributes
2. **PostGIS** enables spatial queries and geometric operations
3. **The LLM** interprets, reasons, and generates insights across both domains

This integration enables questions like:

- "Which communities within 5km of the river are most vulnerable to flooding?"
- "Show me all evacuation centers accessible within 30 minutes for elderly residents"
- "What critical infrastructure depends on this power station, and where is it located?"

---

## Architecture: Three-Layer Geospatial System

```text
┌─────────────────────────────────────────────────────────────────┐
│                    USER QUERIES (Natural Language)              │
│  "Show vulnerable communities near bushfire risk zones"         │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                  LLM REASONING LAYER (Ollama)                   │
│  • Interprets spatial intent                                    │
│  • Translates to PostGIS queries                                │
│  • Generates explanations of spatial patterns                   │
│  • Suggests interventions based on geography                    │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│              KNOWLEDGE GRAPH + SPATIAL LAYER                    │
│  ┌──────────────────┐        ┌───────────────────┐            │
│  │  Entity Graph    │◄──────►│  PostGIS/Geometry │            │
│  │  (relationships) │        │  (locations)      │            │
│  └──────────────────┘        └───────────────────┘            │
│                                                                  │
│  • Entities have geometry (points, polygons)                   │
│  • Relationships can be spatially-constrained                  │
│  • Spatial queries join with graph traversal                   │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MAP VISUALIZATION                            │
│  • Entities as markers/polygons                                 │
│  • Relationships as connecting lines                            │
│  • Spatial analysis results as layers                           │
│  • Interactive query refinement                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Enhanced Database Schema

### 1.1 Spatial Entity Storage

```sql
-- =============================================================================
-- SPATIAL ENTITIES: Extended entity table with comprehensive geometry support
-- =============================================================================

-- Add spatial columns to existing kg_entities table
ALTER TABLE kg_entities 
ADD COLUMN IF NOT EXISTS location_point GEOMETRY(Point, 4326),
ADD COLUMN IF NOT EXISTS location_polygon GEOMETRY(Polygon, 4326),
ADD COLUMN IF NOT EXISTS location_line GEOMETRY(LineString, 4326),
ADD COLUMN IF NOT EXISTS location_multipolygon GEOMETRY(MultiPolygon, 4326);

-- Add spatial metadata
ALTER TABLE kg_entities
ADD COLUMN IF NOT EXISTS geocoding_method VARCHAR(50),  -- 'manual', 'address_geocoded', 'extracted_coords', 'boundary_matched'
ADD COLUMN IF NOT EXISTS geocoding_confidence FLOAT,
ADD COLUMN IF NOT EXISTS address_text TEXT,
ADD COLUMN IF NOT EXISTS spatial_precision VARCHAR(20);  -- 'exact', 'approximate', 'administrative_boundary'

-- Spatial indexes (critical for performance)
CREATE INDEX idx_kg_entities_point ON kg_entities USING gist(location_point);
CREATE INDEX idx_kg_entities_polygon ON kg_entities USING gist(location_polygon);
CREATE INDEX idx_kg_entities_line ON kg_entities USING gist(location_line);
CREATE INDEX idx_kg_entities_multipolygon ON kg_entities USING gist(location_multipolygon);

-- Combined spatial index for any geometry type
CREATE INDEX idx_kg_entities_any_geom ON kg_entities USING gist(
    COALESCE(location_point, ST_Centroid(location_polygon), 
             ST_Centroid(location_line), ST_Centroid(location_multipolygon))
);

-- =============================================================================
-- SPATIAL ZONES: Define hazard zones, administrative boundaries, service areas
-- =============================================================================

CREATE TABLE spatial_zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_type VARCHAR(50) NOT NULL,  -- 'hazard_zone', 'admin_boundary', 'service_area', 'catchment'
    zone_name TEXT NOT NULL,
    zone_subtype VARCHAR(50),        -- e.g., 'flood_100yr', 'bushfire_high_risk', 'LGA'
    
    -- Geometry
    geometry GEOMETRY(Polygon, 4326) NOT NULL,
    
    -- Attributes specific to zone type
    attributes JSONB DEFAULT '{}',
    
    -- Source and quality
    data_source VARCHAR(100),
    data_quality VARCHAR(20),        -- 'authoritative', 'community', 'modeled', 'estimated'
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Sync support
    instance_id UUID,
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_spatial_zones_geom ON spatial_zones USING gist(geometry);
CREATE INDEX idx_spatial_zones_type ON spatial_zones(zone_type, zone_subtype);

-- =============================================================================
-- SPATIAL RELATIONSHIPS: Track spatially-derived relationships
-- =============================================================================

CREATE TABLE spatial_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    source_entity_id UUID REFERENCES kg_entities(id) ON DELETE CASCADE,
    target_entity_id UUID REFERENCES kg_entities(id) ON DELETE CASCADE,
    
    -- Spatial relationship type
    spatial_relation VARCHAR(50) NOT NULL,  -- 'within', 'intersects', 'near', 'along', 'upstream', 'downstream'
    
    -- Measured properties
    distance_meters FLOAT,
    travel_time_minutes FLOAT,
    bearing_degrees FLOAT,
    
    -- Confidence and derivation
    confidence_score FLOAT DEFAULT 1.0,
    derivation_method VARCHAR(50),  -- 'spatial_query', 'network_analysis', 'llm_inferred'
    
    -- Temporal validity
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_spatial_rel UNIQUE (source_entity_id, target_entity_id, spatial_relation)
);

CREATE INDEX idx_spatial_rel_source ON spatial_relationships(source_entity_id);
CREATE INDEX idx_spatial_rel_target ON spatial_relationships(target_entity_id);
CREATE INDEX idx_spatial_rel_type ON spatial_relationships(spatial_relation);

-- =============================================================================
-- SPATIAL ANALYSIS CACHE: Store results of expensive spatial queries
-- =============================================================================

CREATE TABLE spatial_analysis_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    analysis_type VARCHAR(100) NOT NULL,  -- 'buffer_analysis', 'service_area', 'viewshed', 'accessibility'
    parameters JSONB NOT NULL,            -- Query parameters for cache key
    
    -- Results
    result_geometry GEOMETRY,
    result_entities UUID[],               -- Affected entity IDs
    result_data JSONB,
    
    -- Cache metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    cache_key TEXT UNIQUE,
    
    CONSTRAINT valid_cache_entry CHECK (
        result_geometry IS NOT NULL OR 
        result_entities IS NOT NULL OR 
        result_data IS NOT NULL
    )
);

CREATE INDEX idx_spatial_cache_type ON spatial_analysis_cache(analysis_type);
CREATE INDEX idx_spatial_cache_key ON spatial_analysis_cache(cache_key);

-- =============================================================================
-- HELPER FUNCTIONS: Spatial utilities
-- =============================================================================

-- Get primary geometry for any entity (handles multiple geometry columns)
CREATE OR REPLACE FUNCTION get_entity_geometry(entity_id UUID)
RETURNS GEOMETRY AS $$
    SELECT COALESCE(
        location_point,
        ST_Centroid(location_polygon),
        ST_Centroid(location_line),
        ST_Centroid(location_multipolygon)
    )
    FROM kg_entities
    WHERE id = entity_id;
$$ LANGUAGE SQL IMMUTABLE;

-- Calculate distance between two entities
CREATE OR REPLACE FUNCTION entity_distance(entity1_id UUID, entity2_id UUID)
RETURNS FLOAT AS $$
    SELECT ST_Distance(
        get_entity_geometry(entity1_id)::geography,
        get_entity_geometry(entity2_id)::geography
    );
$$ LANGUAGE SQL IMMUTABLE;

-- Check if entity is within a zone
CREATE OR REPLACE FUNCTION entity_in_zone(entity_id UUID, zone_id UUID)
RETURNS BOOLEAN AS $$
    SELECT ST_Within(
        get_entity_geometry(entity_id),
        (SELECT geometry FROM spatial_zones WHERE id = zone_id)
    );
$$ LANGUAGE SQL IMMUTABLE;
```

---

## Part 2: LLM-Enhanced Geocoding Service

### 2.1 Intelligent Geocoding

The LLM can extract, interpret, and validate location information from documents with remarkable accuracy.

```python
# backend/services/geocoding_service.py

from typing import Optional, Tuple, Dict, Any
import json
import asyncio
import httpx
from dataclasses import dataclass

from services.ollama_client import OllamaClient
from db.database import database

@dataclass
class GeocodedLocation:
    """Result of geocoding operation."""
    latitude: float
    longitude: float
    address: str
    confidence: float
    precision: str  # 'exact', 'street', 'suburb', 'town', 'region'
    method: str
    geometry_type: str  # 'point', 'polygon', 'line'
    geometry_wkt: Optional[str] = None  # Well-Known Text for complex geometries


class IntelligentGeocodingService:
    """
    Geocoding service that combines:
    1. LLM for location extraction and interpretation
    2. Geocoding APIs (Nominatim/OpenStreetMap)
    3. Local gazetteers and known place names
    4. Spatial reasoning for ambiguity resolution
    """
    
    def __init__(self):
        self.llm = OllamaClient()
        self.model = "llama3.1:70b"
        
        # Nominatim for geocoding (free, OSM-based)
        self.nominatim_url = "https://nominatim.openstreetmap.org"
        
        # Local gazetteer cache
        self.place_name_cache = {}
    
    async def geocode_entity(
        self,
        entity_name: str,
        entity_type: str,
        context: str,
        attributes: Dict[str, Any]
    ) -> Optional[GeocodedLocation]:
        """
        Main geocoding pipeline for an entity.
        """
        # Step 1: Extract location information using LLM
        location_info = await self._extract_location_info(
            entity_name, entity_type, context, attributes
        )
        
        if not location_info:
            return None
        
        # Step 2: Resolve to coordinates
        geocoded = await self._resolve_to_coordinates(location_info, entity_type)
        
        if not geocoded:
            return None
        
        # Step 3: Validate and enhance with LLM
        validated = await self._validate_location(
            geocoded, entity_name, entity_type, context
        )
        
        return validated
    
    async def _extract_location_info(
        self,
        entity_name: str,
        entity_type: str,
        context: str,
        attributes: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to extract structured location information from context.
        """
        # Check if attributes already have address/location
        if 'address' in attributes or 'location' in attributes:
            return {
                'address': attributes.get('address', attributes.get('location')),
                'source': 'attributes',
                'confidence': 0.9
            }
        
        # Use LLM to extract from context
        prompt = f"""Extract location information for this entity.

ENTITY: {entity_name}
TYPE: {entity_type}
CONTEXT: {context}

TASK:
Extract the most specific location information you can find. Look for:
- Street addresses
- Suburb/town names
- Geographic features (river names, mountain ranges, etc.)
- Relative locations ("5km north of X", "along Y road")
- Coordinates if explicitly mentioned
- Administrative boundaries (LGA, state, etc.)

For this entity type ({entity_type}), focus on:
{self._get_location_hints(entity_type)}

Return ONLY a JSON object:
{{
  "location_type": "address|place_name|geographic_feature|relative|coordinates|boundary",
  "primary_location": "Most specific location string",
  "secondary_locations": ["Additional location context"],
  "coordinates": {{"lat": null, "lon": null}},  // If explicitly mentioned
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation"
}}

If no location information is found, return: {{"found": false}}"""

        response = await self.llm.generate(
            prompt=prompt,
            model=self.model,
            temperature=0.1,
            format="json"
        )
        
        try:
            result = json.loads(response)
            
            if result.get('found') == False:
                return None
            
            return result
            
        except json.JSONDecodeError:
            return None
    
    def _get_location_hints(self, entity_type: str) -> str:
        """Provide entity-specific location extraction hints."""
        hints = {
            "Community": "Look for town/suburb names, population centers, neighborhoods",
            "Agency": "Look for office addresses, headquarters location, service area",
            "Infrastructure": "Look for specific addresses, road names, geographic features",
            "Shelter": "Look for building addresses, facility names",
            "HazardType": "Look for geographic areas, regions, catchments where this hazard occurs",
            "DisasterEvent": "Look for affected areas, impact zones, event location",
        }
        return hints.get(entity_type, "Look for any location references")
    
    async def _resolve_to_coordinates(
        self,
        location_info: Dict[str, Any],
        entity_type: str
    ) -> Optional[GeocodedLocation]:
        """
        Resolve location information to coordinates using multiple methods.
        """
        location_type = location_info.get('location_type')
        primary_location = location_info.get('primary_location')
        
        # If coordinates provided directly
        coords = location_info.get('coordinates', {})
        if coords.get('lat') and coords.get('lon'):
            return GeocodedLocation(
                latitude=coords['lat'],
                longitude=coords['lon'],
                address=primary_location,
                confidence=location_info.get('confidence', 0.9),
                precision='exact',
                method='explicit_coordinates',
                geometry_type='point'
            )
        
        # Try local gazetteer first (fast)
        cached = await self._check_local_gazetteer(primary_location)
        if cached:
            return cached
        
        # Use geocoding API
        geocoded = await self._geocode_with_nominatim(
            primary_location,
            location_info.get('secondary_locations', [])
        )
        
        if geocoded:
            # Cache successful geocode
            await self._cache_gazetteer_entry(primary_location, geocoded)
            return geocoded
        
        # Try LLM-based spatial reasoning for relative locations
        if location_type == 'relative':
            return await self._resolve_relative_location(location_info)
        
        return None
    
    async def _geocode_with_nominatim(
        self,
        location: str,
        additional_context: list
    ) -> Optional[GeocodedLocation]:
        """
        Geocode using Nominatim (OpenStreetMap).
        """
        async with httpx.AsyncClient() as client:
            try:
                # Build search query
                search = location
                if additional_context:
                    search = f"{location}, {', '.join(additional_context)}"
                
                # Nominatim requires a User-Agent
                headers = {
                    'User-Agent': 'CommunityResilienceHub/1.0'
                }
                
                response = await client.get(
                    f"{self.nominatim_url}/search",
                    params={
                        'q': search,
                        'format': 'json',
                        'limit': 1,
                        'polygon_geojson': 1  # Get boundary if available
                    },
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    return None
                
                results = response.json()
                
                if not results:
                    return None
                
                result = results[0]
                
                # Determine precision from OSM type
                osm_type = result.get('type', '')
                precision = self._osm_type_to_precision(osm_type)
                
                # Get geometry
                geometry_type = 'point'
                geometry_wkt = None
                
                if 'geojson' in result:
                    geojson = result['geojson']
                    if geojson.get('type') == 'Polygon':
                        geometry_type = 'polygon'
                        # Convert GeoJSON to WKT
                        geometry_wkt = self._geojson_to_wkt(geojson)
                
                return GeocodedLocation(
                    latitude=float(result['lat']),
                    longitude=float(result['lon']),
                    address=result.get('display_name', location),
                    confidence=0.8,  # Nominatim is generally reliable
                    precision=precision,
                    method='nominatim_geocoded',
                    geometry_type=geometry_type,
                    geometry_wkt=geometry_wkt
                )
                
            except Exception as e:
                print(f"Geocoding failed: {e}")
                return None
    
    def _osm_type_to_precision(self, osm_type: str) -> str:
        """Map OSM types to precision levels."""
        precision_map = {
            'house': 'exact',
            'building': 'exact',
            'street': 'street',
            'suburb': 'suburb',
            'town': 'town',
            'city': 'town',
            'county': 'region',
            'state': 'region',
        }
        return precision_map.get(osm_type.lower(), 'approximate')
    
    def _geojson_to_wkt(self, geojson: dict) -> str:
        """Convert GeoJSON to Well-Known Text."""
        # Simple implementation - in production use shapely
        if geojson['type'] == 'Polygon':
            coords = geojson['coordinates'][0]
            coord_strs = [f"{lon} {lat}" for lon, lat in coords]
            return f"POLYGON(({', '.join(coord_strs)}))"
        return None
    
    async def _resolve_relative_location(
        self,
        location_info: Dict[str, Any]
    ) -> Optional[GeocodedLocation]:
        """
        Use LLM to resolve relative locations like "5km north of Smithville".
        """
        primary = location_info.get('primary_location')
        
        # Use LLM to parse the relative location
        prompt = f"""Parse this relative location description and identify:
1. The reference place
2. The direction (if any)
3. The distance (if any)

LOCATION: {primary}

Return ONLY JSON:
{{
  "reference_place": "Name of the place being referenced",
  "direction": "north|south|east|west|northeast|etc or null",
  "distance_km": number or null
}}"""

        response = await self.llm.generate(
            prompt=prompt,
            model=self.model,
            temperature=0.1,
            format="json"
        )
        
        try:
            parsed = json.loads(response)
            reference_place = parsed.get('reference_place')
            
            # Geocode the reference place first
            ref_geocoded = await self._geocode_with_nominatim(
                reference_place, []
            )
            
            if not ref_geocoded:
                return None
            
            # Calculate offset if direction and distance provided
            if parsed.get('direction') and parsed.get('distance_km'):
                offset_coords = self._calculate_offset(
                    ref_geocoded.latitude,
                    ref_geocoded.longitude,
                    parsed['direction'],
                    parsed['distance_km']
                )
                
                return GeocodedLocation(
                    latitude=offset_coords[0],
                    longitude=offset_coords[1],
                    address=f"{parsed['distance_km']}km {parsed['direction']} of {reference_place}",
                    confidence=0.6,  # Lower confidence for relative locations
                    precision='approximate',
                    method='relative_calculation',
                    geometry_type='point'
                )
            
            # If no offset, just use reference location with lower confidence
            return GeocodedLocation(
                latitude=ref_geocoded.latitude,
                longitude=ref_geocoded.longitude,
                address=f"Near {reference_place}",
                confidence=0.5,
                precision='approximate',
                method='relative_approximate',
                geometry_type='point'
            )
            
        except json.JSONDecodeError:
            return None
    
    def _calculate_offset(
        self,
        lat: float,
        lon: float,
        direction: str,
        distance_km: float
    ) -> Tuple[float, float]:
        """
        Calculate new coordinates given a starting point, direction, and distance.
        Simplified calculation - for production use geopy or similar.
        """
        import math
        
        # Direction to bearing (degrees)
        direction_map = {
            'north': 0, 'northeast': 45, 'east': 90, 'southeast': 135,
            'south': 180, 'southwest': 225, 'west': 270, 'northwest': 315
        }
        bearing = direction_map.get(direction.lower(), 0)
        
        # Earth radius in km
        R = 6371.0
        
        # Convert to radians
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        bearing_rad = math.radians(bearing)
        
        # Calculate new position
        new_lat_rad = math.asin(
            math.sin(lat_rad) * math.cos(distance_km / R) +
            math.cos(lat_rad) * math.sin(distance_km / R) * math.cos(bearing_rad)
        )
        
        new_lon_rad = lon_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(distance_km / R) * math.cos(lat_rad),
            math.cos(distance_km / R) - math.sin(lat_rad) * math.sin(new_lat_rad)
        )
        
        return math.degrees(new_lat_rad), math.degrees(new_lon_rad)
    
    async def _validate_location(
        self,
        geocoded: GeocodedLocation,
        entity_name: str,
        entity_type: str,
        context: str
    ) -> GeocodedLocation:
        """
        Use LLM to validate that the geocoded location makes sense.
        """
        # For high-confidence exact matches, skip validation
        if geocoded.confidence > 0.85 and geocoded.precision == 'exact':
            return geocoded
        
        prompt = f"""Validate if this geocoded location makes sense for the entity.

ENTITY: {entity_name}
TYPE: {entity_type}
CONTEXT: {context}

GEOCODED LOCATION:
- Address: {geocoded.address}
- Coordinates: {geocoded.latitude}, {geocoded.longitude}
- Precision: {geocoded.precision}

Does this location seem reasonable? Consider:
- Does the address match the entity name?
- Is the location type appropriate for this entity type?
- Are there any obvious mismatches?

Return ONLY JSON:
{{
  "is_valid": true/false,
  "confidence_adjustment": -0.3 to +0.3,
  "reasoning": "Brief explanation"
}}"""

        response = await self.llm.generate(
            prompt=prompt,
            model=self.model,
            temperature=0.1,
            format="json"
        )
        
        try:
            validation = json.loads(response)
            
            if not validation.get('is_valid', True):
                # Location seems wrong - reduce confidence significantly
                geocoded.confidence = max(0.1, geocoded.confidence - 0.4)
            else:
                # Apply confidence adjustment
                adjustment = validation.get('confidence_adjustment', 0)
                geocoded.confidence = max(0.0, min(1.0, 
                    geocoded.confidence + adjustment
                ))
            
        except json.JSONDecodeError:
            pass
        
        return geocoded
    
    async def _check_local_gazetteer(
        self, 
        location: str
    ) -> Optional[GeocodedLocation]:
        """Check if location is in local gazetteer cache."""
        # Query database for known places
        result = await database.fetch_one("""
            SELECT latitude, longitude, address, confidence, precision, method
            FROM gazetteer_cache
            WHERE LOWER(place_name) = LOWER(:location)
            AND updated_at > NOW() - INTERVAL '30 days'
        """, {"location": location})
        
        if result:
            return GeocodedLocation(
                latitude=result['latitude'],
                longitude=result['longitude'],
                address=result['address'],
                confidence=result['confidence'],
                precision=result['precision'],
                method=result['method'],
                geometry_type='point'
            )
        
        return None
    
    async def _cache_gazetteer_entry(
        self,
        place_name: str,
        location: GeocodedLocation
    ):
        """Cache a geocoded location for future use."""
        await database.execute("""
            INSERT INTO gazetteer_cache 
                (place_name, latitude, longitude, address, confidence, precision, method)
            VALUES 
                (:place_name, :lat, :lon, :address, :confidence, :precision, :method)
            ON CONFLICT (place_name) 
            DO UPDATE SET
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                updated_at = NOW()
        """, {
            "place_name": place_name,
            "lat": location.latitude,
            "lon": location.longitude,
            "address": location.address,
            "confidence": location.confidence,
            "precision": location.precision,
            "method": location.method
        })


# =============================================================================
# Gazetteer cache table
# =============================================================================
"""
CREATE TABLE gazetteer_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    place_name TEXT UNIQUE NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    address TEXT,
    confidence FLOAT,
    precision VARCHAR(20),
    method VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_gazetteer_place ON gazetteer_cache(place_name);
"""
```

---

## Part 3: Spatial Query Service

### 3.1 Advanced Spatial Queries

```python
# backend/services/spatial_query_service.py

from typing import List, Dict, Any, Optional, Tuple
import json
from datetime import datetime

from db.database import database

class SpatialQueryService:
    """
    Advanced spatial queries combining PostGIS with knowledge graph.
    """
    
    async def find_entities_in_radius(
        self,
        center_lat: float,
        center_lon: float,
        radius_meters: float,
        entity_types: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find all entities within a given radius of a point.
        """
        conditions = ["is_deleted = FALSE"]
        params = {
            "lat": center_lat,
            "lon": center_lon,
            "radius": radius_meters
        }
        
        if entity_types:
            conditions.append("entity_type = ANY(:types)")
            params["types"] = entity_types
        
        # Apply attribute filters
        if filters:
            for key, value in filters.items():
                if key.startswith("attr_"):
                    attr_name = key[5:]
                    conditions.append(f"attributes->>'{attr_name}' = :filter_{attr_name}")
                    params[f"filter_{attr_name}"] = str(value)
        
        query = f"""
            WITH search_point AS (
                SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography AS geog
            )
            SELECT 
                e.id, e.entity_type, e.entity_subtype, e.name, e.attributes,
                e.location_text, e.confidence_score,
                ST_Y(e.location_point::geometry) AS latitude,
                ST_X(e.location_point::geometry) AS longitude,
                ST_Distance(
                    get_entity_geometry(e.id)::geography,
                    search_point.geog
                ) AS distance_meters
            FROM kg_entities e, search_point
            WHERE {' AND '.join(conditions)}
                AND get_entity_geometry(e.id) IS NOT NULL
                AND ST_DWithin(
                    get_entity_geometry(e.id)::geography,
                    search_point.geog,
                    :radius
                )
            ORDER BY distance_meters
        """
        
        results = await database.fetch_all(query, params)
        return [dict(r) for r in results]
    
    async def find_entities_in_zone(
        self,
        zone_id: str,
        entity_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find all entities within a spatial zone.
        """
        conditions = ["e.is_deleted = FALSE"]
        params = {"zone_id": zone_id}
        
        if entity_types:
            conditions.append("e.entity_type = ANY(:types)")
            params["types"] = entity_types
        
        query = f"""
            SELECT 
                e.id, e.entity_type, e.entity_subtype, e.name, e.attributes,
                e.location_text,
                z.zone_name, z.zone_type, z.zone_subtype,
                ST_Y(e.location_point::geometry) AS latitude,
                ST_X(e.location_point::geometry) AS longitude
            FROM kg_entities e
            CROSS JOIN spatial_zones z
            WHERE z.id = :zone_id
                AND {' AND '.join(conditions)}
                AND get_entity_geometry(e.id) IS NOT NULL
                AND ST_Within(
                    get_entity_geometry(e.id),
                    z.geometry
                )
            ORDER BY e.name
        """
        
        results = await database.fetch_all(query, params)
        return [dict(r) for r in results]
    
    async def find_vulnerable_areas(
        self,
        hazard_zone_id: str,
        vulnerability_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Find vulnerable populations within a hazard zone.
        
        Example:
        vulnerability_criteria = {
            "age_over": 65,
            "income_below": 50000,
            "disability": True
        }
        """
        # Get all communities in the hazard zone
        communities = await self.find_entities_in_zone(
            zone_id=hazard_zone_id,
            entity_types=["Community"]
        )
        
        vulnerable_communities = []
        
        for community in communities:
            # Get vulnerable groups in this community
            vulnerable_groups = await database.fetch_all("""
                SELECT 
                    e.id, e.name, e.entity_subtype, e.attributes
                FROM kg_entities e
                JOIN kg_relationships r ON r.source_entity_id = e.id
                WHERE r.target_entity_id = :community_id
                    AND r.relationship_type IN ('locatedIn', 'residesIn')
                    AND e.entity_type = 'VulnerableGroup'
                    AND e.is_deleted = FALSE
            """, {"community_id": community['id']})
            
            if vulnerable_groups:
                community['vulnerable_groups'] = [dict(g) for g in vulnerable_groups]
                vulnerable_communities.append(community)
        
        # Get the hazard zone details
        zone = await database.fetch_one("""
            SELECT zone_name, zone_type, zone_subtype, attributes
            FROM spatial_zones
            WHERE id = :zone_id
        """, {"zone_id": hazard_zone_id})
        
        return {
            "hazard_zone": dict(zone) if zone else None,
            "vulnerable_communities": vulnerable_communities,
            "total_communities": len(communities),
            "vulnerable_count": len(vulnerable_communities)
        }
    
    async def find_critical_infrastructure_at_risk(
        self,
        hazard_zone_id: str
    ) -> List[Dict[str, Any]]:
        """
        Find critical infrastructure within a hazard zone and analyze dependencies.
        """
        # Get all infrastructure in the zone
        infrastructure = await self.find_entities_in_zone(
            zone_id=hazard_zone_id,
            entity_types=["CriticalInfrastructure", "InfrastructureAsset"]
        )
        
        at_risk = []
        
        for infra in infrastructure:
            # Find what/who depends on this infrastructure
            dependencies = await database.fetch_all("""
                SELECT 
                    e.id, e.entity_type, e.name,
                    r.relationship_type, r.attributes
                FROM kg_relationships r
                JOIN kg_entities e ON r.source_entity_id = e.id
                WHERE r.target_entity_id = :infra_id
                    AND r.relationship_type IN ('dependsOn', 'servedBy', 'suppliedBy')
                    AND e.is_deleted = FALSE
            """, {"infra_id": infra['id']})
            
            # Get the services this infrastructure provides
            services = await database.fetch_all("""
                SELECT 
                    e.id, e.entity_type, e.name, e.attributes
                FROM kg_relationships r
                JOIN kg_entities e ON r.target_entity_id = e.id
                WHERE r.source_entity_id = :infra_id
                    AND r.relationship_type = 'provides'
                    AND e.is_deleted = FALSE
            """, {"infra_id": infra['id']})
            
            infra['dependencies'] = [dict(d) for d in dependencies]
            infra['services'] = [dict(s) for s in services]
            infra['dependency_count'] = len(dependencies)
            
            at_risk.append(infra)
        
        # Sort by dependency count (most critical first)
        at_risk.sort(key=lambda x: x['dependency_count'], reverse=True)
        
        return at_risk
    
    async def calculate_service_coverage(
        self,
        service_entity_id: str,
        coverage_radius_meters: float
    ) -> Dict[str, Any]:
        """
        Calculate what areas/populations are covered by a service.
        
        Example: Evacuation center coverage
        """
        # Get service location
        service = await database.fetch_one("""
            SELECT 
                id, name, entity_type, entity_subtype,
                ST_Y(location_point::geometry) AS latitude,
                ST_X(location_point::geometry) AS longitude
            FROM kg_entities
            WHERE id = :id AND is_deleted = FALSE
        """, {"id": service_entity_id})
        
        if not service:
            return {"error": "Service not found"}
        
        # Find all communities within coverage radius
        covered_communities = await self.find_entities_in_radius(
            center_lat=service['latitude'],
            center_lon=service['longitude'],
            radius_meters=coverage_radius_meters,
            entity_types=["Community"]
        )
        
        # Calculate coverage statistics
        total_population = 0
        vulnerable_population = 0
        
        for community in covered_communities:
            # Get population from attributes
            pop = community.get('attributes', {}).get('population', 0)
            total_population += pop
            
            # Get vulnerable groups
            vulnerable = await database.fetch_one("""
                SELECT COUNT(*) as count
                FROM kg_relationships r
                JOIN kg_entities e ON r.source_entity_id = e.id
                WHERE r.target_entity_id = :community_id
                    AND e.entity_type = 'VulnerableGroup'
                    AND r.relationship_type IN ('locatedIn', 'residesIn')
                    AND e.is_deleted = FALSE
            """, {"community_id": community['id']})
            
            vulnerable_population += vulnerable['count'] if vulnerable else 0
        
        # Create coverage polygon (buffer around service point)
        coverage_geojson = await database.fetch_one("""
            SELECT ST_AsGeoJSON(
                ST_Buffer(
                    get_entity_geometry(:service_id)::geography,
                    :radius
                )::geometry
            )::json as coverage_area
        """, {
            "service_id": service_entity_id,
            "radius": coverage_radius_meters
        })
        
        return {
            "service": dict(service),
            "coverage_radius_meters": coverage_radius_meters,
            "covered_communities": len(covered_communities),
            "total_population_covered": total_population,
            "vulnerable_groups_covered": vulnerable_population,
            "coverage_area_geojson": coverage_geojson['coverage_area'] if coverage_geojson else None,
            "communities": covered_communities
        }
    
    async def find_evacuation_routes(
        self,
        from_community_id: str,
        to_shelter_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Find evacuation routes from a community to shelters.
        Returns distance and bearing for each route.
        """
        routes = []
        
        # Get community location
        community = await database.fetch_one("""
            SELECT 
                id, name,
                get_entity_geometry(id) as geom,
                ST_Y(location_point::geometry) AS latitude,
                ST_X(location_point::geometry) AS longitude
            FROM kg_entities
            WHERE id = :id AND is_deleted = FALSE
        """, {"id": from_community_id})
        
        if not community:
            return []
        
        # Get shelter locations and calculate routes
        for shelter_id in to_shelter_ids:
            shelter = await database.fetch_one("""
                SELECT 
                    id, name, entity_type, attributes,
                    get_entity_geometry(id) as geom,
                    ST_Y(location_point::geometry) AS latitude,
                    ST_X(location_point::geometry) AS longitude
                FROM kg_entities
                WHERE id = :id AND is_deleted = FALSE
            """, {"id": shelter_id})
            
            if not shelter:
                continue
            
            # Calculate distance and bearing
            route_info = await database.fetch_one("""
                SELECT 
                    ST_Distance(
                        :community_geom::geography,
                        :shelter_geom::geography
                    ) as distance_meters,
                    degrees(
                        ST_Azimuth(
                            :community_geom,
                            :shelter_geom
                        )
                    ) as bearing_degrees
            """, {
                "community_geom": community['geom'],
                "shelter_geom": shelter['geom']
            })
            
            # Estimate travel time (assuming 40 km/h average speed)
            travel_time_minutes = (route_info['distance_meters'] / 1000) / 40 * 60
            
            # Get shelter capacity if available
            capacity = shelter.get('attributes', {}).get('capacity', 'unknown')
            
            routes.append({
                "shelter": {
                    "id": str(shelter['id']),
                    "name": shelter['name'],
                    "latitude": shelter['latitude'],
                    "longitude": shelter['longitude'],
                    "capacity": capacity
                },
                "distance_meters": round(route_info['distance_meters'], 2),
                "distance_km": round(route_info['distance_meters'] / 1000, 2),
                "bearing_degrees": round(route_info['bearing_degrees'], 1),
                "bearing_cardinal": self._degrees_to_cardinal(route_info['bearing_degrees']),
                "estimated_travel_time_minutes": round(travel_time_minutes, 1)
            })
        
        # Sort by distance (closest first)
        routes.sort(key=lambda x: x['distance_meters'])
        
        return routes
    
    def _degrees_to_cardinal(self, degrees: float) -> str:
        """Convert bearing degrees to cardinal direction."""
        directions = [
            'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
            'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'
        ]
        index = round(degrees / 22.5) % 16
        return directions[index]
    
    async def analyze_spatial_clustering(
        self,
        entity_type: str,
        cluster_distance_meters: float = 5000
    ) -> List[Dict[str, Any]]:
        """
        Find spatial clusters of entities using ST_ClusterDBSCAN.
        Useful for identifying concentrations of risk, resources, etc.
        """
        query = """
            WITH clustered AS (
                SELECT 
                    id, name, entity_subtype, attributes,
                    location_point,
                    ST_ClusterDBSCAN(
                        location_point::geometry,
                        eps := :distance,
                        minpoints := 2
                    ) OVER () AS cluster_id
                FROM kg_entities
                WHERE entity_type = :entity_type
                    AND location_point IS NOT NULL
                    AND is_deleted = FALSE
            )
            SELECT 
                cluster_id,
                COUNT(*) as entity_count,
                array_agg(id) as entity_ids,
                array_agg(name) as entity_names,
                ST_AsGeoJSON(ST_Centroid(ST_Collect(location_point)))::json as centroid,
                ST_AsGeoJSON(ST_ConvexHull(ST_Collect(location_point)))::json as boundary
            FROM clustered
            WHERE cluster_id IS NOT NULL
            GROUP BY cluster_id
            ORDER BY entity_count DESC
        """
        
        # Convert meters to degrees (approximate, for DBSCAN)
        # 1 degree ≈ 111km at equator
        distance_degrees = cluster_distance_meters / 111000
        
        results = await database.fetch_all(query, {
            "entity_type": entity_type,
            "distance": distance_degrees
        })
        
        clusters = []
        for row in results:
            clusters.append({
                "cluster_id": row['cluster_id'],
                "entity_count": row['entity_count'],
                "entity_ids": row['entity_ids'],
                "entity_names": row['entity_names'],
                "centroid": row['centroid'],
                "boundary": row['boundary']
            })
        
        return clusters
```

---

## Part 4: LLM Spatial Reasoning

### 4.1 Natural Language Spatial Queries

```python
# backend/services/llm_spatial_reasoning.py

from typing import Dict, Any, List, Optional
import json

from services.ollama_client import OllamaClient
from services.spatial_query_service import SpatialQueryService
from db.database import database

class LLMSpatialReasoning:
    """
    Use LLM to interpret natural language spatial queries and
    generate insights from spatial analysis results.
    """
    
    def __init__(self):
        self.llm = OllamaClient()
        self.model = "llama3.1:70b"
        self.spatial_query = SpatialQueryService()
    
    async def process_natural_language_query(
        self,
        user_query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point: Convert natural language to spatial query.
        
        Example queries:
        - "Show me all communities within 10km of the river"
        - "Which evacuation centers can serve vulnerable populations in the flood zone?"
        - "What critical infrastructure is at risk in bushfire-prone areas?"
        """
        # Step 1: Parse intent and extract parameters
        query_plan = await self._parse_spatial_intent(user_query, context)
        
        if not query_plan.get('success'):
            return {
                "error": "Could not understand spatial query",
                "suggestion": query_plan.get('suggestion', '')
            }
        
        # Step 2: Execute the spatial query
        results = await self._execute_spatial_query(query_plan)
        
        # Step 3: Generate natural language explanation
        explanation = await self._generate_explanation(
            user_query, query_plan, results
        )
        
        return {
            "query": user_query,
            "query_plan": query_plan,
            "results": results,
            "explanation": explanation,
            "result_count": len(results) if isinstance(results, list) else None
        }
    
    async def _parse_spatial_intent(
        self,
        query: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Use LLM to parse spatial query intent.
        """
        # Get available entity types and zones for context
        entity_types = await self._get_available_entity_types()
        zone_types = await self._get_available_zone_types()
        
        prompt = f"""Parse this spatial query into a structured format.

USER QUERY: {query}

AVAILABLE ENTITY TYPES: {', '.join(entity_types)}
AVAILABLE ZONE TYPES: {', '.join(zone_types)}

Identify:
1. The spatial operation (within_radius, in_zone, near, between, etc.)
2. The entity types being queried
3. Any distance/radius specifications
4. Any zones or reference locations
5. Any filters or conditions

Return ONLY JSON:
{{
  "success": true,
  "operation": "within_radius|in_zone|coverage_analysis|at_risk_analysis|route_analysis",
  "entity_types": ["Community", "Agency"],
  "parameters": {{
    "center_location": "name or coordinates",
    "radius_meters": 5000,
    "zone_name": "Flood Zone",
    "zone_type": "hazard_zone",
    "filters": {{"attribute_name": "value"}}
  }},
  "intent_description": "Brief description of what user wants"
}}

If you cannot parse the query, return:
{{
  "success": false,
  "suggestion": "Helpful suggestion on how to rephrase"
}}"""

        response = await self.llm.generate(
            prompt=prompt,
            model=self.model,
            temperature=0.1,
            format="json"
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "success": False,
                "suggestion": "Please try rephrasing your query with specific locations or entity types."
            }
    
    async def _execute_spatial_query(
        self,
        query_plan: Dict[str, Any]
    ) -> Any:
        """
        Execute the parsed spatial query.
        """
        operation = query_plan.get('operation')
        params = query_plan.get('parameters', {})
        entity_types = query_plan.get('entity_types', [])
        
        if operation == 'within_radius':
            # Need to geocode the center location first
            center_location = params.get('center_location')
            
            if isinstance(center_location, str):
                # Geocode the location
                from services.geocoding_service import IntelligentGeocodingService
                geocoder = IntelligentGeocodingService()
                
                geocoded = await geocoder._geocode_with_nominatim(
                    center_location, []
                )
                
                if not geocoded:
                    return {"error": f"Could not find location: {center_location}"}
                
                center_lat = geocoded.latitude
                center_lon = geocoded.longitude
            else:
                center_lat = params.get('center_lat')
                center_lon = params.get('center_lon')
            
            radius = params.get('radius_meters', 5000)
            
            return await self.spatial_query.find_entities_in_radius(
                center_lat=center_lat,
                center_lon=center_lon,
                radius_meters=radius,
                entity_types=entity_types
            )
        
        elif operation == 'in_zone':
            # Find the zone first
            zone_name = params.get('zone_name')
            zone_type = params.get('zone_type')
            
            zone = await database.fetch_one("""
                SELECT id FROM spatial_zones
                WHERE zone_name ILIKE :name
                    AND zone_type = :type
                    AND is_deleted = FALSE
                LIMIT 1
            """, {"name": f"%{zone_name}%", "type": zone_type})
            
            if not zone:
                return {"error": f"Could not find zone: {zone_name}"}
            
            return await self.spatial_query.find_entities_in_zone(
                zone_id=str(zone['id']),
                entity_types=entity_types
            )
        
        elif operation == 'coverage_analysis':
            service_name = params.get('service_name')
            radius = params.get('radius_meters', 10000)
            
            # Find the service entity
            service = await database.fetch_one("""
                SELECT id FROM kg_entities
                WHERE name ILIKE :name
                    AND entity_type IN ('Shelter', 'Agency', 'Facility')
                    AND is_deleted = FALSE
                LIMIT 1
            """, {"name": f"%{service_name}%"})
            
            if not service:
                return {"error": f"Could not find service: {service_name}"}
            
            return await self.spatial_query.calculate_service_coverage(
                service_entity_id=str(service['id']),
                coverage_radius_meters=radius
            )
        
        elif operation == 'at_risk_analysis':
            zone_name = params.get('zone_name')
            
            zone = await database.fetch_one("""
                SELECT id FROM spatial_zones
                WHERE zone_name ILIKE :name
                    AND zone_type = 'hazard_zone'
                    AND is_deleted = FALSE
                LIMIT 1
            """, {"name": f"%{zone_name}%"})
            
            if not zone:
                return {"error": f"Could not find hazard zone: {zone_name}"}
            
            return await self.spatial_query.find_critical_infrastructure_at_risk(
                hazard_zone_id=str(zone['id'])
            )
        
        elif operation == 'route_analysis':
            from_location = params.get('from_location')
            to_locations = params.get('to_locations', [])
            
            # Find the source community
            community = await database.fetch_one("""
                SELECT id FROM kg_entities
                WHERE name ILIKE :name
                    AND entity_type = 'Community'
                    AND is_deleted = FALSE
                LIMIT 1
            """, {"name": f"%{from_location}%"})
            
            if not community:
                return {"error": f"Could not find community: {from_location}"}
            
            # Find shelters
            shelters = await database.fetch_all("""
                SELECT id FROM kg_entities
                WHERE entity_type = 'Shelter'
                    AND is_deleted = FALSE
            """)
            
            shelter_ids = [str(s['id']) for s in shelters]
            
            return await self.spatial_query.find_evacuation_routes(
                from_community_id=str(community['id']),
                to_shelter_ids=shelter_ids
            )
        
        return {"error": "Unknown operation"}
    
    async def _generate_explanation(
        self,
        original_query: str,
        query_plan: Dict[str, Any],
        results: Any
    ) -> str:
        """
        Generate natural language explanation of results.
        """
        # Summarize results for LLM
        result_summary = self._summarize_results(results)
        
        prompt = f"""Generate a natural language explanation of these spatial query results.

ORIGINAL QUERY: {original_query}

QUERY PLAN: {json.dumps(query_plan, indent=2)}

RESULTS SUMMARY: {result_summary}

Generate a clear, concise explanation that:
1. Confirms what was found
2. Highlights key findings
3. Notes any important patterns or risks
4. Suggests follow-up actions if appropriate

Keep it under 150 words. Be specific and actionable."""

        explanation = await self.llm.generate(
            prompt=prompt,
            model=self.model,
            temperature=0.3
        )
        
        return explanation.strip()
    
    def _summarize_results(self, results: Any) -> str:
        """Create a summary of results for LLM."""
        if isinstance(results, dict):
            if 'error' in results:
                return f"Error: {results['error']}"
            
            # Summarize different result types
            summary_parts = []
            
            if 'covered_communities' in results:
                summary_parts.append(
                    f"{results['covered_communities']} communities covered"
                )
                if 'total_population_covered' in results:
                    summary_parts.append(
                        f"{results['total_population_covered']} total population"
                    )
            
            if 'vulnerable_communities' in results:
                summary_parts.append(
                    f"{len(results['vulnerable_communities'])} vulnerable communities found"
                )
            
            if 'dependency_count' in results:
                summary_parts.append(
                    f"{results['dependency_count']} dependencies identified"
                )
            
            return '; '.join(summary_parts) if summary_parts else json.dumps(results)
        
        elif isinstance(results, list):
            if len(results) == 0:
                return "No results found"
            
            return f"{len(results)} entities found: {', '.join([r.get('name', 'Unknown') for r in results[:5]])}" + (
                f" and {len(results) - 5} more" if len(results) > 5 else ""
            )
        
        return str(results)
    
    async def _get_available_entity_types(self) -> List[str]:
        """Get list of entity types that exist in the KG."""
        result = await database.fetch_all("""
            SELECT DISTINCT entity_type
            FROM kg_entities
            WHERE is_deleted = FALSE
            ORDER BY entity_type
        """)
        return [r['entity_type'] for r in result]
    
    async def _get_available_zone_types(self) -> List[str]:
        """Get list of zone types that exist."""
        result = await database.fetch_all("""
            SELECT DISTINCT zone_type
            FROM spatial_zones
            WHERE is_deleted = FALSE
            ORDER BY zone_type
        """)
        return [r['zone_type'] for r in result]
    
    async def generate_spatial_insights(
        self,
        entity_id: str
    ) -> Dict[str, str]:
        """
        Generate LLM insights about an entity's spatial context.
        """
        # Get entity with spatial context
        entity = await database.fetch_one("""
            SELECT 
                e.*,
                ST_Y(e.location_point::geometry) AS latitude,
                ST_X(e.location_point::geometry) AS longitude
            FROM kg_entities e
            WHERE e.id = :id AND e.is_deleted = FALSE
        """, {"id": entity_id})
        
        if not entity:
            return {"error": "Entity not found"}
        
        # Get nearby entities
        nearby = await self.spatial_query.find_entities_in_radius(
            center_lat=entity['latitude'],
            center_lon=entity['longitude'],
            radius_meters=5000
        )
        
        # Get zones this entity is in
        zones = await database.fetch_all("""
            SELECT zone_name, zone_type, zone_subtype
            FROM spatial_zones
            WHERE ST_Within(
                (SELECT get_entity_geometry(:id)),
                geometry
            )
            AND is_deleted = FALSE
        """, {"id": entity_id})
        
        # Generate insights
        prompt = f"""Analyze the spatial context of this entity and provide insights.

ENTITY:
- Name: {entity['name']}
- Type: {entity['entity_type']}
- Location: {entity['latitude']}, {entity['longitude']}

NEARBY ENTITIES (within 5km):
{self._format_entity_list(nearby[:10])}

ZONES THIS ENTITY IS IN:
{self._format_zone_list(zones)}

Generate insights covering:
1. Strategic location advantages/disadvantages
2. Potential risks based on nearby hazards
3. Accessibility considerations
4. Resource proximity
5. Recommendations for planning

Be specific and actionable. Focus on emergency management relevance."""

        insights = await self.llm.generate(
            prompt=prompt,
            model=self.model,
            temperature=0.4
        )
        
        return {
            "entity_id": entity_id,
            "entity_name": entity['name'],
            "insights": insights.strip(),
            "nearby_count": len(nearby),
            "zones": [dict(z) for z in zones]
        }
    
    def _format_entity_list(self, entities: List[Dict]) -> str:
        """Format entity list for LLM prompt."""
        return '\n'.join([
            f"- {e['name']} ({e['entity_type']}) - {e.get('distance_meters', 0):.0f}m away"
            for e in entities
        ])
    
    def _format_zone_list(self, zones: List[Dict]) -> str:
        """Format zone list for LLM prompt."""
        if not zones:
            return "- Not in any defined zones"
        return '\n'.join([
            f"- {z['zone_name']} ({z['zone_type']}: {z.get('zone_subtype', 'N/A')})"
            for z in zones
        ])
```

---

## Part 5: Frontend Map Integration

### 5.1 Interactive Map Component

```svelte
<!-- frontend/src/lib/components/maps/KGMap.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import maplibregl from 'maplibre-gl';
  import 'maplibre-gl/dist/maplibre-gl.css';
  
  export let initialView = {
    center: [144.9631, -37.8136], // Melbourne
    zoom: 10
  };
  
  let mapContainer;
  let map;
  let selectedEntityId = null;
  
  // Layer visibility toggles
  let layers = {
    communities: true,
    agencies: true,
    infrastructure: true,
    hazardZones: true,
    shelters: true
  };
  
  onMount(async () => {
    // Initialize map
    map = new maplibregl.Map({
      container: mapContainer,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '© OpenStreetMap'
          }
        },
        layers: [
          {
            id: 'osm',
            type: 'raster',
            source: 'osm'
          }
        ]
      },
      center: initialView.center,
      zoom: initialView.zoom
    });
    
    map.on('load', async () => {
      await loadKGLayers();
    });
  });
  
  async function loadKGLayers() {
    // Load communities
    const communities = await fetch('/api/kg/geo/Community').then(r => r.json());
    map.addSource('communities', {
      type: 'geojson',
      data: communities
    });
    
    map.addLayer({
      id: 'communities',
      type: 'circle',
      source: 'communities',
      paint: {
        'circle-radius': 8,
        'circle-color': '#3b82f6',
        'circle-stroke-width': 2,
        'circle-stroke-color': '#ffffff'
      }
    });
    
    // Load agencies
    const agencies = await fetch('/api/kg/geo/Agency').then(r => r.json());
    map.addSource('agencies', {
      type: 'geojson',
      data: agencies
    });
    
    map.addLayer({
      id: 'agencies',
      type: 'circle',
      source: 'agencies',
      paint: {
        'circle-radius': 6,
        'circle-color': '#10b981',
        'circle-stroke-width': 1,
        'circle-stroke-color': '#ffffff'
      }
    });
    
    // Load infrastructure
    const infrastructure = await fetch('/api/kg/geo/CriticalInfrastructure')
      .then(r => r.json());
    map.addSource('infrastructure', {
      type: 'geojson',
      data: infrastructure
    });
    
    map.addLayer({
      id: 'infrastructure',
      type: 'circle',
      source: 'infrastructure',
      paint: {
        'circle-radius': 7,
        'circle-color': '#f59e0b',
        'circle-stroke-width': 2,
        'circle-stroke-color': '#ffffff'
      }
    });
    
    // Load shelters
    const shelters = await fetch('/api/kg/geo/Shelter').then(r => r.json());
    map.addSource('shelters', {
      type: 'geojson',
      data: shelters
    });
    
    map.addLayer({
      id: 'shelters',
      type: 'symbol',
      source: 'shelters',
      layout: {
        'icon-image': 'marker',
        'icon-size': 1.5,
        'text-field': ['get', 'name'],
        'text-offset': [0, 1.5],
        'text-size': 12
      }
    });
    
    // Load hazard zones
    const hazardZones = await fetch('/api/spatial/zones?type=hazard_zone')
      .then(r => r.json());
    map.addSource('hazard-zones', {
      type: 'geojson',
      data: hazardZones
    });
    
    map.addLayer({
      id: 'hazard-zones',
      type: 'fill',
      source: 'hazard-zones',
      paint: {
        'fill-color': [
          'match',
          ['get', 'zone_subtype'],
          'flood_100yr', '#ef4444',
          'bushfire_high', '#dc2626',
          'storm_surge', '#3b82f6',
          '#64748b'
        ],
        'fill-opacity': 0.3
      }
    });
    
    map.addLayer({
      id: 'hazard-zones-outline',
      type: 'line',
      source: 'hazard-zones',
      paint: {
        'line-color': '#000000',
        'line-width': 2,
        'line-dasharray': [2, 2]
      }
    });
    
    // Add click handlers
    map.on('click', 'communities', handleEntityClick);
    map.on('click', 'agencies', handleEntityClick);
    map.on('click', 'infrastructure', handleEntityClick);
    map.on('click', 'shelters', handleEntityClick);
    
    // Add hover effects
    map.on('mouseenter', 'communities', () => { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'communities', () => { map.getCanvas().style.cursor = ''; });
  }
  
  async function handleEntityClick(e) {
    const feature = e.features[0];
    selectedEntityId = feature.id;
    
    // Show popup with entity info
    new maplibregl.Popup()
      .setLngLat(e.lngLat)
      .setHTML(`
        <div class="entity-popup">
          <h3>${feature.properties.name}</h3>
          <p><strong>Type:</strong> ${feature.properties.entity_type}</p>
          <button onclick="window.viewEntityDetails('${feature.id}')">
            View Details
          </button>
        </div>
      `)
      .addTo(map);
    
    // Fetch and show spatial insights
    const insights = await fetch(`/api/spatial/insights/${feature.id}`)
      .then(r => r.json());
    
    console.log('Spatial insights:', insights);
  }
  
  function toggleLayer(layerName) {
    const visibility = layers[layerName] ? 'visible' : 'none';
    map.setLayoutProperty(layerName, 'visibility', visibility);
  }
  
  async function queryNaturalLanguage(query) {
    const response = await fetch('/api/spatial/nl-query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });
    
    const result = await response.json();
    
    // Visualize results on map
    if (result.results && Array.isArray(result.results)) {
      highlightEntitiesOnMap(result.results);
    }
    
    return result;
  }
  
  function highlightEntitiesOnMap(entities) {
    // Create temporary layer for highlighted entities
    const highlights = {
      type: 'FeatureCollection',
      features: entities.map(e => ({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [e.longitude, e.latitude]
        },
        properties: e
      }))
    };
    
    if (map.getSource('highlights')) {
      map.getSource('highlights').setData(highlights);
    } else {
      map.addSource('highlights', {
        type: 'geojson',
        data: highlights
      });
      
      map.addLayer({
        id: 'highlights',
        type: 'circle',
        source: 'highlights',
        paint: {
          'circle-radius': 12,
          'circle-color': '#ef4444',
          'circle-stroke-width': 3,
          'circle-stroke-color': '#ffffff',
          'circle-opacity': 0.8
        }
      });
    }
    
    // Fit map to show all highlighted entities
    if (entities.length > 0) {
      const bounds = new maplibregl.LngLatBounds();
      entities.forEach(e => {
        bounds.extend([e.longitude, e.latitude]);
      });
      map.fitBounds(bounds, { padding: 50 });
    }
  }
  
  // Expose to window for external calls
  if (typeof window !== 'undefined') {
    window.viewEntityDetails = (entityId) => {
      // Navigate to entity detail page
      window.location.href = `/knowledge-graph/entities/${entityId}`;
    };
  }
</script>

<div class="map-container">
  <div class="map-controls">
    <div class="layer-toggles">
      <h4>Layers</h4>
      {#each Object.entries(layers) as [key, visible]}
        <label>
          <input
            type="checkbox"
            bind:checked={layers[key]}
            on:change={() => toggleLayer(key)}
          />
          {key}
        </label>
      {/each}
    </div>
    
    <div class="spatial-query">
      <h4>Spatial Query</h4>
      <input
        type="text"
        placeholder="e.g., communities within 5km of flood zone"
        on:keydown={(e) => {
          if (e.key === 'Enter') {
            queryNaturalLanguage(e.target.value);
          }
        }}
      />
    </div>
  </div>
  
  <div bind:this={mapContainer} class="map" />
</div>

<style>
  .map-container {
    position: relative;
    width: 100%;
    height: 600px;
  }
  
  .map {
    width: 100%;
    height: 100%;
  }
  
  .map-controls {
    position: absolute;
    top: 10px;
    right: 10px;
    background: white;
    padding: 1rem;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    z-index: 1;
    max-width: 250px;
  }
  
  .layer-toggles label {
    display: block;
    margin: 0.5rem 0;
  }
  
  .spatial-query {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #e5e7eb;
  }
  
  .spatial-query input {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 4px;
  }
</style>
```

---

## Part 6: Use Case Examples

### 6.1 Practical Scenarios

#### Scenario 1: Vulnerability Assessment

**Query:** "Show me communities with elderly populations in bushfire risk zones"

**LLM Processing:**

1. Identifies entity types: Community, VulnerableGroup
2. Identifies spatial constraint: within bushfire risk zones
3. Identifies attribute filter: elderly population

**Execution:**

```python
# Find bushfire zones
bushfire_zones = await database.fetch_all("""
    SELECT id FROM spatial_zones
    WHERE zone_type = 'hazard_zone'
      AND zone_subtype LIKE '%bushfire%'
""")

results = []
for zone in bushfire_zones:
    # Find communities in zone
    communities = await spatial_query.find_entities_in_zone(
        zone_id=zone['id'],
        entity_types=['Community']
    )
    
    # Filter for elderly population
    for community in communities:
        elderly = await database.fetch_one("""
            SELECT COUNT(*) as count
            FROM kg_relationships r
            JOIN kg_entities e ON r.source_entity_id = e.id
            WHERE r.target_entity_id = :community_id
              AND e.entity_type = 'VulnerableGroup'
              AND e.entity_subtype = 'elderly'
        """, {"community_id": community['id']})
        
        if elderly['count'] > 0:
            community['elderly_count'] = elderly['count']
            results.append(community)
```

**LLM Explanation:**
"Found 12 communities with elderly populations in bushfire-prone areas. The highest concentration is in Hilltop (45 elderly residents) which is in a high-risk zone. Immediate actions: verify evacuation plans include elderly-specific considerations, ensure adequate shelter capacity with medical facilities, confirm emergency contacts for all elderly residents."

#### Scenario 2: Resource Allocation

**Query:** "Where should we locate a new evacuation center to maximize coverage?"

**LLM Processing:**

1. Identifies goal: optimal location
2. Considers: population distribution, existing shelter coverage, hazard zones
3. Suggests analysis: coverage gap analysis

**Execution:**

```python
# Get all communities
communities = await kg_query.list_entities(entity_type='Community')

# Get existing shelters
existing_shelters = await kg_query.list_entities(entity_type='Shelter')

# Calculate coverage gaps
uncovered_communities = []
for community in communities:
    # Check if within 10km of any shelter
    covered = False
    for shelter in existing_shelters:
        distance = await database.fetch_one("""
            SELECT ST_Distance(
                get_entity_geometry(:c_id)::geography,
                get_entity_geometry(:s_id)::geography
            ) as distance
        """, {"c_id": community['id'], "s_id": shelter['id']})
        
        if distance['distance'] < 10000:  # 10km
            covered = True
            break
    
    if not covered:
        uncovered_communities.append(community)

# Find optimal location using clustering
optimal_point = await database.fetch_one("""
    SELECT 
        ST_Y(ST_Centroid(ST_Collect(location_point))) as lat,
        ST_X(ST_Centroid(ST_Collect(location_point))) as lon
    FROM kg_entities
    WHERE id = ANY(:ids)
""", {"ids": [c['id'] for c in uncovered_communities]})
```

**LLM Explanation:**
"Analysis shows 8 communities lack evacuation center access within 10km. The optimal location for a new center is approximately -37.82, 144.95 (near Fairfield). This would provide coverage to all 8 communities (total population: 15,000) and reduce maximum evacuation distance from 18km to 7km. The location is accessible via main roads and outside flood zones."

---

## Part 7: Implementation Priorities

### Phase 1: Basic Spatial (Week 1)

- [ ] Enhanced database schema with PostGIS
- [ ] Basic geocoding for entities
- [ ] Simple radius queries
- [ ] GeoJSON export for map display

### Phase 2: LLM Integration (Week 2)

- [ ] Intelligent geocoding with LLM
- [ ] Natural language spatial query parsing
- [ ] Spatial insight generation

### Phase 3: Advanced Analysis (Week 3)

- [ ] Coverage analysis
- [ ] Risk assessment queries
- [ ] Dependency mapping with spatial context
- [ ] Route analysis

### Phase 4: Frontend (Week 4)

- [ ] Interactive map component
- [ ] Layer toggles and filtering
- [ ] Natural language query interface
- [ ] Spatial analysis visualizations

---

## Key Takeaways

The combination of **Knowledge Graph + GIS + LLM** creates capabilities that exceed the sum of parts:

1. **LLM extracts spatial information** from unstructured documents
2. **PostGIS provides spatial intelligence** (proximity, containment, routing)
3. **Knowledge Graph connects spatial and semantic relationships**
4. **LLM interprets and explains** spatial patterns in natural language

This enables emergency managers to ask questions like:

- "What's our response capacity in flood-affected areas?"
- "Show vulnerable populations near the fire"
- "Where are the coverage gaps in our shelter network?"

And get answers that are:

- **Spatially accurate** (PostGIS)
- **Relationally complete** (Knowledge Graph)
- **Naturally explained** (LLM)

The system becomes truly intelligent about geography, not just decorating maps with pins.
