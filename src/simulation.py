"""
Klasa reprezentująca symulację budynku z windami.
"""

import random
from .config import NUM_ELEVATORS, NUM_FLOORS, MAX_CAPACITY, CALL_ARRIVAL_RATE
from .passenger import Passenger
from .elevator import Elevator


class BuildingSimulation:
    """
    Reprezentuje symulację budynku z systemem wind.
    
    Obsługuje dwa różne algorytmy sterowania ruchem wind:
    
    Algorytm A:
    - Pasażer wzywający windę wybiera kierunek jazdy (góra/dół) przy wezwaniu
    - System przypisuje najbliższą windę znajdującą się najbliżej piętra wezwania
    - Prosty algorytm bez optymalizacji grupowania kursów
    
    Algorytm B:
    - Pasażer wybiera piętro docelowe przed wejściem do windy
    - System optymalizuje przypisanie, wybierając windę, która może najlepiej
      zrealizować żądanie, uwzględniając grupowanie kursów o podobnych kierunkach
    - Zaawansowany algorytm z optymalizacją kosztu (odległość, obciążenie, grupowanie)
    """
    
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

            # Przypisz windę według wybranego algorytmu:
            # - Algorytm A: najbliższa winda (prosty wybór)
            # - Algorytm B: optymalna winda (uwzględnia grupowanie kursów)
            assigned = self._assign_call(p)
            assigned.add_call(p)
            # dalej p zostanie zabrany przez windę w jej run -> _stop_at_floor

    def _assign_call(self, passenger):
        """
        Przypisuje wezwanie pasażera do odpowiedniej windy.
        Wybiera odpowiednią metodę w zależności od typu algorytmu.
    
        Args:
            passenger: Obiekt Passenger
            
        Returns:
            Elevator: Winda przypisana do obsługi wezwania
        """
        if self.algorithm_type == 'A':
            return self._assign_algorithm_a(passenger)
        else:  # algorytm B
            return self._assign_algorithm_b(passenger)
    
    def _assign_algorithm_a(self, passenger):
        """
        Algorytm A: Pasażer wybiera kierunek jazdy (góra/dół) przy wezwaniu.
        System przypisuje najbliższą windę znajdującą się najbliżej piętra wezwania.
        
        Różnica: Prosty wybór najbliższej windy, bez optymalizacji grupowania kursów.
        
        Args:
            passenger: Obiekt Passenger z wybranym kierunkiem (passenger.direction)
            
        Returns:
            Elevator: Najbliższa winda
        """
        # Algorytm A: po prostu najbliższa winda
        # Pasażer już wybrał kierunek (passenger.direction), więc przypisujemy
        # najbliższą windę niezależnie od jej aktualnego stanu
        nearest_elevator = min(
            self.elevators, 
            key=lambda e: abs(e.current_floor - passenger.call_floor)
        )
        return nearest_elevator
    
    def _assign_algorithm_b(self, passenger):
        """
        Algorytm B: Pasażer wybiera piętro docelowe przed wejściem do windy.
        System optymalizuje przypisanie, wybierając windę, która może najlepiej
        zrealizować żądanie, uwzględniając grupowanie kursów o podobnych kierunkach.
        
        Różnica: Optymalizacja kosztu uwzględniająca:
        - Odległość do piętra wezwania
        - Obecne obciążenie windy
        - Możliwość grupowania z innymi pasażerami (bonus za kursy w tym samym kierunku)
        - Kara za przeciwny kierunek
        
        Args:
            passenger: Obiekt Passenger z wybranym piętrem docelowym
            
        Returns:
            Elevator: Winda z najmniejszym kosztem przypisania
        """
        # Algorytm B: optymalizacja kosztu z uwzględnieniem grupowania
        costs = [(e.calculate_cost_b(passenger), e) for e in self.elevators]
        best_elevator = min(costs, key=lambda x: x[0])[1]
        return best_elevator
    
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

