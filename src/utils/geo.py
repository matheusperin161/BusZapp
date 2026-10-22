"""Utility functions for geolocation calculations."""
from math import radians, sin, cos, sqrt, atan2


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the distance in meters between two GPS coordinates."""
    R = 6371.0  # Earth radius in km
    lat1_r, lon1_r, lat2_r, lon2_r = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a)) * 1000  # meters


def calculate_speed(prev_lat: float, prev_lon: float, curr_lat: float, curr_lon: float, time_diff_seconds: float) -> float:
    """Calculate speed in km/h from two positions and elapsed time."""
    if time_diff_seconds <= 0:
        return 0.0
    distance_km = haversine(prev_lat, prev_lon, curr_lat, curr_lon) / 1000.0
    time_hours = time_diff_seconds / 3600.0
    return round(distance_km / time_hours, 2) if time_hours > 0 else 0.0


def calculate_eta(distance_meters: float, speed_kmh: float, default_speed: float = 30.0) -> float:
    """Calculate estimated time of arrival in minutes."""
    effective_speed = speed_kmh if speed_kmh > 0 else default_speed
    return round((distance_meters / 1000.0) / effective_speed * 60.0, 1)


def find_next_stops_with_eta(bus_lat: float, bus_lon: float, speed_kmh: float, route) -> list:
    """Return upcoming stop points with ETA for each, starting from the closest."""
    stop_points = sorted(route.stop_points, key=lambda sp: sp.order)

    if not stop_points:
        return []

    # Find closest stop
    closest_index = min(
        range(len(stop_points)),
        key=lambda i: haversine(bus_lat, bus_lon, stop_points[i].latitude, stop_points[i].longitude)
    )

    stops_with_eta = []
    cumulative_distance = 0.0

    for i in range(closest_index, len(stop_points)):
        stop = stop_points[i]
        if i == closest_index:
            cumulative_distance = haversine(bus_lat, bus_lon, stop.latitude, stop.longitude)
        else:
            prev = stop_points[i - 1]
            cumulative_distance += haversine(prev.latitude, prev.longitude, stop.latitude, stop.longitude)

        stops_with_eta.append({
            'stop': stop,
            'distance_meters': cumulative_distance,
            'eta_minutes': calculate_eta(cumulative_distance, speed_kmh),
        })

    return stops_with_eta


VELOCIDADE_PADRAO_KMH = 20.0  # usada quando o trecho não tem tempo estimado cadastrado


def _distancia_ate_segmento(lat, lon, a, b):
    """Distância (m) do ponto ao segmento a→b e fração do segmento já percorrida (0..1).

    Projeção equiretangular local — suficiente para trechos urbanos curtos.
    """
    k = cos(radians(lat))
    ax, ay = a.longitude * k, a.latitude
    bx, by = b.longitude * k, b.latitude
    px, py = lon * k, lat
    dx, dy = bx - ax, by - ay
    comprimento2 = dx * dx + dy * dy
    t = 0.0 if comprimento2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / comprimento2))
    proj_lat, proj_lon = ay + t * dy, (ax + t * dx) / k
    return haversine(lat, lon, proj_lat, proj_lon), t


def proxima_parada(lat: float, lon: float, paradas: list, sentido: str = 'ida') -> dict | None:
    """Próxima parada e minutos estimados até ela (CA08.6).

    `paradas` são StopPoints da linha. O tempo de cada trecho vem de
    `tempo_ate_proxima_min` (cadastrado no sentido de ida, vale igual para a volta);
    sem ele, usa a distância do trecho a VELOCIDADE_PADRAO_KMH.
    O ônibus é encaixado no trecho mais próximo e o tempo é proporcional ao que falta dele.
    """
    ida = sorted(paradas, key=lambda p: p.order)
    if not ida:
        return None
    tempos = {}
    for i in range(len(ida) - 1):
        a, b = ida[i], ida[i + 1]
        if a.tempo_ate_proxima_min is not None:
            minutos = a.tempo_ate_proxima_min
        else:
            minutos = calculate_eta(haversine(a.latitude, a.longitude, b.latitude, b.longitude), VELOCIDADE_PADRAO_KMH)
        tempos[(a.id, b.id)] = tempos[(b.id, a.id)] = minutos

    ordem = ida if sentido == 'ida' else list(reversed(ida))
    if len(ordem) == 1:
        unica = ordem[0]
        distancia = haversine(lat, lon, unica.latitude, unica.longitude)
        return {'parada': unica, 'distancia_m': distancia, 'eta_min': calculate_eta(distancia, VELOCIDADE_PADRAO_KMH)}

    melhor = None
    for i in range(len(ordem) - 1):
        a, b = ordem[i], ordem[i + 1]
        distancia, t = _distancia_ate_segmento(lat, lon, a, b)
        if melhor is None or distancia < melhor[0]:
            melhor = (distancia, t, a, b)

    _, t, a, b = melhor
    eta = round(tempos[(a.id, b.id)] * (1.0 - t), 1)
    return {
        'parada': b,
        'distancia_m': haversine(lat, lon, b.latitude, b.longitude),
        'eta_min': eta,
    }
