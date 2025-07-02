"""
test_screening_factor.py

Test scrip    print(f"Earth wire indices: {system.earth_indices}")
    
    # Ensure impedance matrix is calculated
    Z = system.calculate_series_impedance_matrix()
    
    # Manual screening factor calculation
    print("\n--- Manual Screening Factor Calculation ---")
    
    faulted_phase_label = 'R'
    faulted_phase_idx = [i for i, c in enumerate(system.conductors) if c['label'] == faulted_phase_label][0]
    pipeline_idx = system.pipeline_indices[0]
    earth_indices = system.earth_indices
    
    print(f"Faulted phase '{faulted_phase_label}' index: {faulted_phase_idx}")
    print(f"Pipeline index: {pipeline_idx}")
    print(f"Earth wire indices: {earth_indices}")
    
    # Get sub-matricese screening factor calculation step by step.
"""

import numpy as np
import json
import sys
import os
from io import StringIO

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from transmission_line_calculator import MultiConductorSystem, load_system_from_json
from fault_analysis import FaultAnalyzer

def test_screening_factor_calculation():
    """
    Test the screening factor calculation with detailed output.
    """
    print("=" * 80)
    print("SCREENING FACTOR CALCULATION TEST")
    print("=" * 80)
    
    # Load system (suppress detailed output)
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    
    try:
        conductors, freq, rho_earth = load_system_from_json(
            'example_10_5_ohl.json', 'example_10_5_pipeline.json')
        system = MultiConductorSystem(conductors, freq, rho_earth)
    finally:
        sys.stdout = old_stdout
    
    print("\n--- System Configuration ---")
    for i, c in enumerate(system.conductors):
        print(f"Conductor {i}: {c['label']} at ({c['x']:.2f}, {c['y']:.2f}) m")
    
    print(f"\nPhase indices: {system.phase_indices}")
    print(f"Earth indices: {system.earth_indices}")
    print(f"Earth wire indices: {system.earth_indices}")
    
    # Ensure impedance matrix is calculated
    Z = system.calculate_series_impedance_matrix()
    
    # Manual screening factor calculation
    print("\n--- Manual Screening Factor Calculation ---")
    
    faulted_phase_label = 'R'
    faulted_phase_idx = [i for i, c in enumerate(system.conductors) if c['label'] == faulted_phase_label][0]
    pipeline_idx = system.pipeline_indices[0]
    earth_indices = system.earth_indices
    
    print(f"Faulted phase '{faulted_phase_label}' index: {faulted_phase_idx}")
    print(f"Pipeline index: {pipeline_idx}")
    print(f"Earth wire indices: {earth_indices}")
    
    # Get sub-matrices
    Z_ep = Z[np.ix_(earth_indices, [faulted_phase_idx])]
    Z_ee = Z[np.ix_(earth_indices, earth_indices)]
    Z_pe = Z[np.ix_([pipeline_idx], earth_indices)]
    Z_pp = Z[faulted_phase_idx, pipeline_idx]
    
    print(f"\nZ_ep (earth to faulted phase): {Z_ep}")
    print(f"Z_ee (earth self-impedance): {Z_ee}")
    print(f"Z_pe (pipeline to earth): {Z_pe}")
    print(f"Z_pp (pipeline to faulted phase): {Z_pp:.4f}")
    
    # Calculate shielding term
    shielding_term = (Z_pe @ np.linalg.inv(Z_ee) @ Z_ep)[0, 0]
    k_manual = 1 - (shielding_term / Z_pp)
    
    print(f"\nShielding term: {shielding_term:.4f}")
    print(f"Manual screening factor k: {k_manual:.4f}")
    
    # Test using FaultAnalyzer
    print("\n--- FaultAnalyzer Calculation ---")
    fault_analyzer = FaultAnalyzer(system)
    k_analyzer = fault_analyzer.calculate_screening_factor(faulted_phase_label)
    
    print(f"\nComparison:")
    print(f"Manual k:   {k_manual:.6f}")
    print(f"Analyzer k: {k_analyzer:.6f}")
    print(f"Difference: {abs(k_manual - k_analyzer):.8f}")
    
    # Validate fault EMF calculation
    print("\n--- Fault EMF Validation ---")
    fault_current = 13000 + 0j  # A
    
    # Manual calculation
    emf_manual = -Z_pp * k_manual * fault_current
    print(f"Manual EMF calculation: {abs(emf_manual):.1f} V/km")
    
    # Analyzer calculation
    emf_analyzer = fault_analyzer.calculate_fault_emf(fault_current, faulted_phase_label)
    print(f"Analyzer EMF: {abs(emf_analyzer):.1f} V/km")
    
    print(f"\nTextbook reference: 1203.4 V/km")
    print(f"Error from textbook: {abs(abs(emf_analyzer) - 1203.4) / 1203.4 * 100:.1f}%")
    
    return k_analyzer, emf_analyzer

if __name__ == '__main__':
    k, emf = test_screening_factor_calculation()
