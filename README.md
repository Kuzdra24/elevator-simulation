# Symulacja Systemu Wind

Projekt symulacji systemu zarządzania windami w budynku z porównaniem dwóch algorytmów przypisania.

## Wymagania

- Python 3.8+
- pip

## Instalacja

1. Utwórz i aktywuj wirtualne środowisko:
```bash
python3 -m venv venv
source venv/bin/activate  # Na macOS/Linux
# lub
venv\Scripts\activate  # Na Windows
```

2. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

## Uruchomienie

**Ważne:** Przed uruchomieniem upewnij się, że środowisko wirtualne jest aktywowane!

```bash
# Aktywuj środowisko wirtualne
source venv/bin/activate  # Na macOS/Linux
# lub
venv\Scripts\activate    # Na Windows

# Uruchom program
python main.py
```

Alternatywnie, możesz uruchomić bezpośrednio z Pythonem ze środowiska:
```bash
venv/bin/python main.py  # Na macOS/Linux
venv\Scripts\python main.py  # Na Windows
```

## Struktura projektu

```
projekt/
├── src/                    # Kod źródłowy
│   ├── __init__.py        # Eksporty modułu
│   ├── config.py          # Parametry konfiguracyjne
│   ├── passenger.py       # Klasa Passenger
│   ├── elevator.py        # Klasa Elevator
│   ├── simulation.py      # Klasa BuildingSimulation
│   └── stats.py           # Funkcje uruchamiania i wizualizacji
├── notebooks/             # Notebooki Jupyter do analizy
├── main.py                # Główny punkt wejścia
├── requirements.txt       # Lista zależności Python
├── .gitignore             # Pliki ignorowane przez Git
└── README.md              # Ten plik
```

## Moduły

### `src/config.py`
Zawiera wszystkie parametry konfiguracyjne systemu:
- Liczba wind i pięter
- Pojemność wind
- Czasy przejazdu i postoju
- Współczynnik generowania wezwań

### `src/passenger.py`
Klasa `Passenger` reprezentująca pasażera w systemie.

### `src/elevator.py`
Klasa `Elevator` reprezentująca windę z logiką ruchu i obsługi pasażerów.

### `src/simulation.py`
Klasa `BuildingSimulation` zarządzająca całą symulacją:
- Generator wezwań pasażerów
- Przypisanie wind do wezwań (algorytmy A i B)
- Zbieranie statystyk

### `src/stats.py`
Funkcje pomocnicze:
- `run_simulation()` - uruchamia symulację
- `plot_results()` - wizualizuje wyniki

## Zależności

- `simpy` - biblioteka do symulacji zdarzeń dyskretnych
- `numpy` - obliczenia numeryczne
- `matplotlib` - wizualizacja wyników
- `ipykernel` - jądro Jupyter dla notebooków (opcjonalne, jeśli używasz notebooków)

## Użycie jako moduł

Możesz również używać modułu w swoich skryptach:

```python
from src import run_simulation, plot_results

resA = run_simulation('A', 500, seed=42)
resB = run_simulation('B', 500, seed=42)
plot_results(resA, resB, 500)
```

## Algorytmy

- **Algorytm A**: Przypisuje najbliższą windę, która może obsłużyć pasażera zgodnie z kierunkiem
- **Algorytm B**: Używa funkcji kosztu uwzględniającej odległość, obciążenie, kierunek i bonus za pasażerów "po drodze"
