import numpy as np
import random
import matplotlib.pyplot as plt
import simpy
from .config import NUM_ELEVATORS
from .simulation import BuildingSimulation


def run_simulation(alg_type, sim_time, seed=None):
    """
    Uruchamia symulację systemu wind.
    
    Args:
        alg_type: Typ algorytmu ('A' lub 'B')
        sim_time: Czas trwania symulacji
        seed: Ziarno losowości (opcjonalne)
        
    Returns:
        dict: Słownik z wynikami symulacji
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    print(f"\n=== Start symulacji: {alg_type}, czas: {sim_time} ===")
    env = simpy.Environment()
    simulation = BuildingSimulation(env, NUM_ELEVATORS, alg_type)
    env.run(until=sim_time)

    # Zbierz statystyki
    elevator_stats = simulation.collect_statistics()

    avg_wait = np.mean(simulation.wait_times) if simulation.wait_times else 0.0
    avg_trip = np.mean(simulation.trip_times) if simulation.trip_times else 0.0
    total_movement = sum(s['total_movement_time'] for s in elevator_stats)
    total_served = simulation.total_passengers_served[0]

    print("WYNIKI:")
    print(f"Średni czas oczekiwania: {avg_wait:.2f}")
    print(f"Średni czas przejazdu: {avg_trip:.2f}")
    print(f"Łącznie obsłużonych pasażerów: {total_served}")
    print(f"Łączny czas ruchu wind: {total_movement:.2f}")

    return {
        'algorithm': alg_type,
        'avg_wait': avg_wait,
        'avg_trip': avg_trip,
        'total_served': total_served,
        'total_movement': total_movement
    }


def plot_results(results_A, results_B, sim_time):
    """
    Tworzy wykresy porównawcze wyników dwóch algorytmów.
    
    Args:
        results_A: Wyniki algorytmu A
        results_B: Wyniki algorytmu B
        sim_time: Czas symulacji (do tytułu)
    """
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
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()*1.01, 
                   f'{bar.get_height():.2f}', ha='center')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()

