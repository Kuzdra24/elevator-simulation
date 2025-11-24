"""
Parametry konfiguracyjne systemu symulacji wind.
"""

# Parametry systemu
NUM_ELEVATORS = 6      # Liczba wind
NUM_FLOORS = 30        # Piętra 0..9
MAX_CAPACITY = 14       # Maksymalna liczba osób na raz

# Parametry czasowe
TIME_PER_FLOOR = 4     # czas przejazdu między piętrami
STOP_TIME = 1          # czas postoju na piętrze (wsiadanie/wysiadanie)
CALL_ARRIVAL_RATE = 0.6  # lambda dla wykładniczego rozkładu między zgłoszeniami

