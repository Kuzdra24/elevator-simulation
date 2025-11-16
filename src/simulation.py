"""
Klasa reprezentująca symulację budynku z windami.
"""

import random
from .config import NUM_ELEVATORS, NUM_FLOORS, MAX_CAPACITY, CALL_ARRIVAL_RATE
from .passenger import Passenger
from .elevator import Elevator


class BuildingSimulation:
    """Reprezentuje symulację budynku z systemem wind."""
    
    def __init__(self, env, num_elevators, algorithm_type):
        """
        Inicjalizuje symulację budynku.
        
        Args:
            env: Środowisko simpy
            num_elevators: Liczba wind w budynku
            algorithm_type: Typ algorytmu przypisania ('A' lub 'B')
        """
        self.env = env
        self.algorithm_type = algorithm_type
        self.pending_calls = {}  # floor -> list[Passenger]
        
        # Statystyki symulacji
        self.wait_times = []
        self.trip_times = []
        self.total_passengers_served = [0]  # lista z jednym elementem dla mutowalności
        self.elevator_stats = []
        
        # Utwórz windy
        self.elevators = [Elevator(env, i, self) for i in range(num_elevators)]
        
        # Uruchom generator wezwań
        self.env.process(self.call_generator())

    def call_generator(self):
        """Generator wezwań pasażerów zgodnie z rozkładem wykładniczym."""
        while True:
            inter = random.expovariate(CALL_ARRIVAL_RATE)
            yield self.env.timeout(inter)

            call_floor = random.randint(0, NUM_FLOORS - 1)
            target_floor = call_floor
            while target_floor == call_floor:
                target_floor = random.randint(0, NUM_FLOORS - 1)
            num_people = random.randint(1, MAX_CAPACITY)

            p = Passenger(self.env, call_floor, target_floor, num_people)

            # najpierw dodajemy do pending_calls (żeby winda znalazła pasażera jak przyjedzie natychmiast)
            if call_floor not in self.pending_calls:
                self.pending_calls[call_floor] = []
            self.pending_calls[call_floor].append(p)

            # przypisz windę według algorytmu
            assigned = self._assign_call(p)
            assigned.add_call(p)
            # dalej p zostanie zabrany przez windę w jej run -> _stop_at_floor

    def _assign_call(self, passenger):
        """
        Przypisuje wezwanie pasażera do odpowiedniej windy.
        
        Args:
            passenger: Obiekt Passenger
            
        Returns:
            Elevator: Winda przypisana do obsługi wezwania
        """
        if self.algorithm_type == 'A':
            # wybierz najbliższą windę, która może obsłużyć (albo najbliższa ogólnie)
            candidates = []
            for e in self.elevators:
                distance = abs(e.current_floor - passenger.call_floor)
                can_serve = (e.direction == 0) or (
                    e.direction == passenger.direction and
                    ((e.direction == 1 and e.current_floor <= passenger.call_floor) or
                     (e.direction == -1 and e.current_floor >= passenger.call_floor))
                )
                if can_serve:
                    candidates.append((distance, e))
            if candidates:
                return min(candidates, key=lambda x: x[0])[1]
            # brak kandydatów spełniających kierunkowo -> najbliższa winda
            return min(self.elevators, key=lambda e: abs(e.current_floor - passenger.call_floor))

        else:  # algorytm B
            costs = [(e.calculate_cost_b(passenger), e) for e in self.elevators]
            return min(costs, key=lambda x: x[0])[1]
    
    def collect_statistics(self):
        """
        Zbiera statystyki z wszystkich wind.
        
        Returns:
            list: Lista słowników ze statystykami każdej windy
        """
        stats = []
        for e in self.elevators:
            stats.append({
                'id': e.id,
                'total_movement_time': e.total_movement_time,
                'floors_traveled': e.floors_traveled
            })
        return stats

