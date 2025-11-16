"""
Klasa reprezentująca windę w systemie.
"""

import simpy
from .config import TIME_PER_FLOOR, STOP_TIME, MAX_CAPACITY


class Elevator:
    """Reprezentuje windę w budynku."""
    
    def __init__(self, env, eid, simulation):
        """
        Inicjalizuje windę.
        
        Args:
            env: Środowisko simpy
            eid: Unikalne ID windy
            simulation: Referencja do obiektu BuildingSimulation
        """
        self.env = env
        self.id = eid
        self.current_floor = 0
        self.direction = 0  # -1 (dół), 0 (stoi), 1 (góra)
        self.passengers = []  # lista Passenger
        self.requests = {}    # floor -> dir (external) lub True (internal)
        self.queue = simpy.Store(env)
        self.simulation = simulation

        # statystyki
        self.total_movement_time = 0.0
        self.floors_traveled = 0

        self.process = env.process(self.run())

    def run(self):
        """Główna pętla działania windy."""
        while True:
            if not self.requests:
                # czekaj aż ktoś doda żądanie
                self.direction = 0
                yield self.queue.get()
                # po wybudzeniu pętla się powtarza i wybierze cel
            else:
                target_floor, new_dir = self._get_next_destination()
                if target_floor == self.current_floor:
                    # może obsłużyć zatrzymanie bez ruchu (np. osoba wejdzie)
                    yield self.env.process(self._stop_at_floor())
                    # Jeśli nadal jest żądanie na tym samym piętrze i nie można go obsłużyć, usuń je
                    if self.current_floor in self.requests:
                        waiting = self.simulation.pending_calls.get(self.current_floor, [])
                        if not waiting:
                            # Nie ma już oczekujących, usuń żądanie
                            del self.requests[self.current_floor]
                        elif all(not ((self.direction == 0) or (p.direction == self.direction)) 
                                for p in waiting):
                            # Wszyscy pasażerowie jadą w przeciwnym kierunku, usuń żądanie
                            del self.requests[self.current_floor]
                else:
                    if new_dir != 0:
                        self.direction = new_dir
                    yield self.env.process(self._move_to_floor(target_floor))
                    yield self.env.process(self._stop_at_floor())

    def _get_current_load(self):
        """Zwraca aktualne obciążenie windy (liczba osób)."""
        return sum(p.num_people for p in self.passengers)

    def _get_next_destination(self):
        """
        Wybiera najbliższe żądanie zgodne z kierunkiem, albo najbliższe ogólnie.
        
        Returns:
            tuple: (target_floor, new_direction)
        """
        floors = sorted(self.requests.keys())
        if not floors:
            return self.current_floor, 0

        # jeśli jedziemy w górę - celuj w najmniejsze piętro > current
        if self.direction == 1:
            up = [f for f in floors if f > self.current_floor]
            if up:
                return min(up), 1
            # brak w górę -> szukaj dół
            down = [f for f in floors if f < self.current_floor]
            if down:
                return max(down), -1

        elif self.direction == -1:
            down = [f for f in floors if f < self.current_floor]
            if down:
                return max(down), -1
            up = [f for f in floors if f > self.current_floor]
            if up:
                return min(up), 1

        # jeśli stoi albo nie ma kierunku preferowanego -> wybierz najbliższe (minimalna odległość)
        closest = min(floors, key=lambda f: abs(f - self.current_floor))
        new_dir = 1 if closest > self.current_floor else -1 if closest < self.current_floor else 0
        return closest, new_dir

    def _move_to_floor(self, target_floor):
        """
        Symuluje ruch windy do określonego piętra.
        
        Args:
            target_floor: Piętro docelowe
        """
        if target_floor == self.current_floor:
            return
        floors_to_move = abs(target_floor - self.current_floor)
        travel_time = floors_to_move * TIME_PER_FLOOR
        self.total_movement_time += travel_time
        self.floors_traveled += floors_to_move
        self.direction = 1 if target_floor > self.current_floor else -1
        # symulacja ruchu
        yield self.env.timeout(travel_time)
        self.current_floor = target_floor

    def _stop_at_floor(self):
        """Obsługuje zatrzymanie windy na piętrze: wysiadanie i wsiadanie pasażerów."""
        # Wysiadanie
        passengers_out = [p for p in self.passengers if p.target_floor == self.current_floor]
        if passengers_out:
            yield self.env.timeout(STOP_TIME)
            for p in passengers_out:
                p.record_dropoff(
                    self.simulation.trip_times,
                    self.simulation.total_passengers_served
                )
            self.passengers = [p for p in self.passengers if p.target_floor != self.current_floor]

        # Jeśli było zewnętrzne żądanie tego piętra i nie ma już oczekujących, usuń
        if self.current_floor in self.simulation.pending_calls:
            if not self.simulation.pending_calls[self.current_floor]:
                if self.current_floor in self.requests:
                    del self.requests[self.current_floor]

        # Wsiadanie
        # Sprawdź listę oczekujących na tym piętrze (jeśli istnieje)
        waiting = self.simulation.pending_calls.get(self.current_floor, [])
        if waiting:
            # wybierz pasażerów, którzy mogą wsiąść
            passengers_to_board = []
            for p in list(waiting):  # kopiujemy listę bo będziemy usuwać elementy
                can_board_direction = (self.direction == 0) or (p.direction == self.direction)
                if can_board_direction and (self._get_current_load() + p.num_people) <= MAX_CAPACITY:
                    passengers_to_board.append(p)
                else:
                    # jeśli winda jedzie przeciwnie i nie stoi, to pomijamy tych pasażerów
                    # ale nie blokujemy wybrania kolejnych jeśli winda stoi
                    if self.direction != 0 and not can_board_direction:
                        continue
                    # jeśli brak miejsca -> nie bierzemy więcej (zakładamy FIFO przy braku miejsca)
                    if (self._get_current_load() + p.num_people) > MAX_CAPACITY:
                        break

            if passengers_to_board:
                yield self.env.timeout(STOP_TIME)
                for p in passengers_to_board:
                    p.record_pickup(self.id, self.simulation.wait_times)
                    self.passengers.append(p)
                    # zadanie wewnętrzne: cel pasażera
                    self.requests[p.target_floor] = True
                    # usuń z kolejki oczekujących w budynku
                    waiting.remove(p)

            # jeśli po wsiadaniu nikt nie czeka na tym piętrze, usuń zewnętrzne żądanie (u tej windy)
            if not waiting and self.current_floor in self.requests:
                if self.requests[self.current_floor] != True:
                    # jeśli entry nie było wewnętrznym żądaniem, usuń
                    del self.requests[self.current_floor]
            # Jeśli są jeszcze oczekujący, ale żaden nie może wsiąść (przeciwny kierunek lub brak miejsca),
            # usuń żądanie dla tej windy, aby nie blokować innych wind
            elif waiting and self.current_floor in self.requests:
                can_any_board = any(
                    ((self.direction == 0) or (p.direction == self.direction)) and
                    (self._get_current_load() + p.num_people) <= MAX_CAPACITY
                    for p in waiting
                )
                if not can_any_board and self.requests[self.current_floor] != True:
                    # Żaden pasażer nie może wsiąść, usuń żądanie dla tej windy
                    del self.requests[self.current_floor]

    def add_call(self, passenger):
        """
        Dodaje zewnętrzne wezwanie (piętro -> kierunek) i budzi windę jeśli stoi.
        
        Args:
            passenger: Obiekt Passenger reprezentujący wezwanie
        """
        call_floor = passenger.call_floor
        call_dir = passenger.direction
        # jeśli nie ma wpisu albo jest inny (zastąp/upewnij się że kierunek zapisany)
        self.requests[call_floor] = call_dir
        # obudź jeśli stoi i pusta
        if self.direction == 0 and not self.passengers:
            self.queue.put(True)

    def calculate_cost_b(self, passenger):
        """
        Funkcja kosztu dla algorytmu B.
        
        Args:
            passenger: Obiekt Passenger
            
        Returns:
            float: Koszt przypisania tego pasażera do tej windy
        """
        distance = abs(self.current_floor - passenger.call_floor)
        travel_cost = distance * TIME_PER_FLOOR
        capacity_cost = self._get_current_load() * 5
        # czy on-route?
        is_on_route = (self.direction == passenger.direction) and (
            (self.direction == 1 and passenger.call_floor >= self.current_floor) or
            (self.direction == -1 and passenger.call_floor <= self.current_floor)
        )
        grouping_bonus = travel_cost * 0.5 if is_on_route else 0
        direction_penalty = 0
        if self.direction != 0 and self.direction != passenger.direction and not is_on_route:
            direction_penalty = 100
        if self._get_current_load() + passenger.num_people > MAX_CAPACITY:
            capacity_cost += 5000
        cost = travel_cost + capacity_cost + direction_penalty - grouping_bonus
        return cost

