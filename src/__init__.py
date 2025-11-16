"""
Moduł symulacji systemu wind.

Eksportuje główne klasy i funkcje:
- Passenger: klasa reprezentująca pasażera
- Elevator: klasa reprezentująca windę
- BuildingSimulation: klasa reprezentująca symulację budynku
- run_simulation: funkcja uruchamiająca symulację
- plot_results: funkcja wizualizująca wyniki
"""

from .passenger import Passenger
from .elevator import Elevator
from .simulation import BuildingSimulation
from .stats import run_simulation, plot_results
from . import config

__all__ = [
    'Passenger',
    'Elevator',
    'BuildingSimulation',
    'run_simulation',
    'plot_results',
    'config'
]

