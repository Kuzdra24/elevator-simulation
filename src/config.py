"""
Parametry konfiguracyjne systemu symulacji wind.
"""

# Parametry systemu
NUM_ELEVATORS = 3      # Liczba wind
NUM_FLOORS = 10        # Piętra 0..9
MAX_CAPACITY = 8       # Maksymalna liczba osób na raz

# Parametry czasowe
TIME_PER_FLOOR = 2     # czas przejazdu między piętrami
STOP_TIME = 1          # czas postoju na piętrze (wsiadanie/wysiadanie)
CALL_ARRIVAL_RATE = 0.2  # lambda dla wykładniczego rozkładu między zgłoszeniami

