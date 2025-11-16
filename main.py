"""
Główny punkt wejścia do programu symulacji systemu wind.
"""

from src.stats import run_simulation, plot_results

if __name__ == "__main__":
    SIM_TIME = 500  # Czas symulacji
    resA = run_simulation('A', SIM_TIME, seed=42)
    resB = run_simulation('B', SIM_TIME, seed=42)
    plot_results(resA, resB, SIM_TIME)

