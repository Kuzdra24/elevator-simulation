import simpy
import numpy as np
import random
import matplotlib.pyplot as plt

# --- PARAMETRY SYSTEMU ---
NUM_ELEVATORS = 3      # Liczba wind
NUM_FLOORS = 10        # Piętra 0..9
MAX_CAPACITY = 8       # Maksymalna liczba osób na raz

TIME_PER_FLOOR = 2     # czas przejazdu między piętrami
STOP_TIME = 1          # czas postoju na piętrze (wsiadanie/wysiadanie)
CALL_ARRIVAL_RATE = 0.2  # lambda dla wykładniczego rozkładu między zgłoszeniami

# --- GLOBALNE MIARY ---
WAIT_TIMES = []
TRIP_TIMES = []
TOTAL_PASSENGERS_SERVED = 0
ELEVATOR_STATS = []

SIMULATION = None  # będzie ustawione przy starcie symulacji


class Passenger:
    def __init__(self, env, call_floor, target_floor, num_people):
        self.env = env
        self.call_floor = call_floor
        self.target_floor = target_floor
        self.direction = 1 if target_floor > call_floor else -1
        self.num_people = num_people
        self.arrival_time = env.now
        self.trip_start_time = None

    def record_pickup(self, elevator_id):
        pickup_time = self.env.now
        wait_time = pickup_time - self.arrival_time
        WAIT_TIMES.append(wait_time)
        self.trip_start_time = pickup_time
        # debug:
        # print(f"[{self.env.now:.1f}] Passenger from {self.call_floor} picked by elevator {elevator_id}")

    def record_dropoff(self):
        global TOTAL_PASSENGERS_SERVED
        dropoff_time = self.env.now
        trip_time = dropoff_time - self.trip_start_time
        TRIP_TIMES.append(trip_time)
        TOTAL_PASSENGERS_SERVED += self.num_people
        # debug:
        # print(f"[{self.env.now:.1f}] Passenger to {self.target_floor} dropped off (trip {trip_time:.1f})")


class Elevator:
    def __init__(self, env, eid):
        self.env = env
        self.id = eid
        self.current_floor = 0
        self.direction = 0  # -1,0,1
        self.passengers = []  # lista Passenger
        self.requests = {}    # floor -> dir (external) lub True (internal)
        self.queue = simpy.Store(env)

        # statystyki
        self.total_movement_time = 0.0
        self.floors_traveled = 0

        self.process = env.process(self.run())

    def run(self):
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
                        waiting = SIMULATION.pending_calls.get(self.current_floor, [])
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
        return sum(p.num_people for p in self.passengers)

    def _get_next_destination(self):
        """Wybierz najbliższe żądanie zgodne z kierunkiem, albo najbliższe ogólnie."""
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
        # Wysiadanie
        passengers_out = [p for p in self.passengers if p.target_floor == self.current_floor]
        if passengers_out:
            yield self.env.timeout(STOP_TIME)
            for p in passengers_out:
                p.record_dropoff()
            self.passengers = [p for p in self.passengers if p.target_floor != self.current_floor]

        # Jeśli było zewnętrzne żądanie tego piętra i nie ma już oczekujących, usuń
        if self.current_floor in SIMULATION.pending_calls:
            if not SIMULATION.pending_calls[self.current_floor]:
                if self.current_floor in self.requests:
                    del self.requests[self.current_floor]

        # Wsiadanie
        # Sprawdź listę oczekujących na tym piętrze (jeśli istnieje)
        waiting = SIMULATION.pending_calls.get(self.current_floor, [])
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
                    p.record_pickup(self.id)
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
        """Dodaj external call (piętro -> kierunek) i obudź windę jeśli stoi."""
        call_floor = passenger.call_floor
        call_dir = passenger.direction
        # jeśli nie ma wpisu albo jest inny (zastąp/upewnij się że kierunek zapisany)
        self.requests[call_floor] = call_dir
        # obudź jeśli stoi i pusta
        if self.direction == 0 and not self.passengers:
            self.queue.put(True)

    def calculate_cost_b(self, passenger):
        """Funkcja kosztu dla algorytmu B."""
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


class BuildingSimulation:
    def __init__(self, env, num_elevators, algorithm_type):
        self.env = env
        self.elevators = [Elevator(env, i) for i in range(num_elevators)]
        self.algorithm_type = algorithm_type
        self.pending_calls = {}  # floor -> list[Passenger]
        self.env.process(self.call_generator())

    def call_generator(self):
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


def run_simulation(alg_type, sim_time, seed=None):
    global WAIT_TIMES, TRIP_TIMES, TOTAL_PASSENGERS_SERVED, ELEVATOR_STATS, SIMULATION
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    WAIT_TIMES = []
    TRIP_TIMES = []
    TOTAL_PASSENGERS_SERVED = 0
    ELEVATOR_STATS = []

    print(f"\n=== Start symulacji: {alg_type}, czas: {sim_time} ===")
    env = simpy.Environment()
    SIMULATION = BuildingSimulation(env, NUM_ELEVATORS, alg_type)
    env.run(until=sim_time)

    for e in SIMULATION.elevators:
        ELEVATOR_STATS.append({
            'id': e.id,
            'total_movement_time': e.total_movement_time,
            'floors_traveled': e.floors_traveled
        })

    avg_wait = np.mean(WAIT_TIMES) if WAIT_TIMES else 0.0
    avg_trip = np.mean(TRIP_TIMES) if TRIP_TIMES else 0.0
    total_movement = sum(s['total_movement_time'] for s in ELEVATOR_STATS)

    print("WYNIKI:")
    print(f"Średni czas oczekiwania: {avg_wait:.2f}")
    print(f"Średni czas przejazdu: {avg_trip:.2f}")
    print(f"Łącznie obsłużonych pasażerów: {TOTAL_PASSENGERS_SERVED}")
    print(f"Łączny czas ruchu wind: {total_movement:.2f}")

    return {
        'algorithm': alg_type,
        'avg_wait': avg_wait,
        'avg_trip': avg_trip,
        'total_served': TOTAL_PASSENGERS_SERVED,
        'total_movement': total_movement
    }


def plot_results(results_A, results_B, sim_time):
    metrics = {
        'Średni czas oczekiwania': (results_A['avg_wait'], results_B['avg_wait']),
        'Średni czas przejazdu': (results_A['avg_trip'], results_B['avg_trip']),
        'Łączny czas ruchu wind': (results_A['total_movement'], results_B['total_movement']),
        'Łącznie obsłużonych pasażerów': (results_A['total_served'], results_B['total_served'])
    }
    labels = ['Alg A', 'Alg B']
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(f'Porównanie (T={sim_time})')

    axes = axes.flatten()
    for i, (title, (a, b)) in enumerate(metrics.items()):
        ax = axes[i]
        values = [a, b]
        bars = ax.bar(labels, values)
        ax.set_title(title)
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()*1.01, f'{bar.get_height():.2f}', ha='center')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()


if __name__ == "__main__":
    SIM_TIME = 500  # Zmniejszony czas symulacji dla szybszych testów
    resA = run_simulation('A', SIM_TIME, seed=42)
    resB = run_simulation('B', SIM_TIME, seed=42)
    plot_results(resA, resB, SIM_TIME)
