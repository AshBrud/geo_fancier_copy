from django.contrib.gis.geos import MultiPolygon, Polygon, LineString, MultiLineString

GEO_WIDGET_ATTRS = {
    'class': 'form-control geom-input',
    'rows': 4,
    'placeholder': 'Collez le GeoJSON ici ou dessinez sur la carte...',
}


def to_multipolygon(geom):
    if isinstance(geom, Polygon):
        return MultiPolygon(geom, srid=geom.srid or 4326)
    return geom


def to_multilinestring(geom):
    if isinstance(geom, LineString):
        return MultiLineString(geom, srid=geom.srid or 4326)
    return geom
