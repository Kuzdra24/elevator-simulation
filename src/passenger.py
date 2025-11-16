"""
Klasa reprezentująca pasażera w systemie wind.
"""


class Passenger:
    """Reprezentuje pasażera oczekującego na windę lub jadącego windą."""
    
    def __init__(self, env, call_floor, target_floor, num_people):
        """
        Inicjalizuje pasażera.
        
        Args:
            env: Środowisko simpy
            call_floor: Piętro, z którego pasażer wzywa windę
            target_floor: Piętro docelowe
            num_people: Liczba osób w grupie
        """
        self.env = env
        self.call_floor = call_floor
        self.target_floor = target_floor
        self.direction = 1 if target_floor > call_floor else -1
        self.num_people = num_people
        self.arrival_time = env.now
        self.trip_start_time = None

    def record_pickup(self, elevator_id, wait_times):
        """
        Zapisuje moment wsiadania pasażera do windy.
        
        Args:
            elevator_id: ID windy, która zabrała pasażera
            wait_times: Lista czasów oczekiwania (do aktualizacji)
        """
        pickup_time = self.env.now
        wait_time = pickup_time - self.arrival_time
        wait_times.append(wait_time)
        self.trip_start_time = pickup_time

    def record_dropoff(self, trip_times, total_passengers_served):
        """
        Zapisuje moment wysiadania pasażera z windy.
        
        Args:
            trip_times: Lista czasów przejazdu (do aktualizacji)
            total_passengers_served: Licznik obsłużonych pasażerów (do aktualizacji)
        """
        dropoff_time = self.env.now
        trip_time = dropoff_time - self.trip_start_time
        trip_times.append(trip_time)
        total_passengers_served[0] += self.num_people

