"""
run_interference_study.py

Main orchestration script for comprehensive pipeline interference analysis.
Integrates geometric processing with electromagnetic calculations.
"""

import json
import numpy as np
import sys
import os

# Add current directory to Python path to ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from transmission_line_calculator import MultiConductorSystem, load_system_from_json
from geometry_processor import Sectionizer

def run_study(ohl_config_file, pipeline_config_file, ohl_traj_file, pl_traj_file, currents_file):
    """
    Orchestrates the entire pipeline interference study.
    
    Args:
        ohl_config_file (str): Path to OHL configuration JSON
        pipeline_config_file (str): Path to pipeline configuration JSON  
        ohl_traj_file (str): Path to OHL trajectory JSON
        pl_traj_file (str): Path to pipeline trajectory JSON
        currents_file (str): Path to system currents JSON
    """
    print("=== COMPREHENSIVE PIPELINE INTERFERENCE STUDY ===")
    print("Phase 2: Geometric Processing + Electromagnetic Analysis\n")

    # --- 1. Load Trajectories and Sectionize ---
    print("--- 1. Loading Trajectories and Sectionizing ---")
    with open(ohl_traj_file, 'r') as f:
        ohl_traj_data = json.load(f)
        ohl_traj = ohl_traj_data['coordinates_m']
        print(f"OHL Route: {ohl_traj_data['name']}")
        
    with open(pl_traj_file, 'r') as f:
        pl_traj_data = json.load(f)
        pl_traj = pl_traj_data['coordinates_m']
        print(f"Pipeline Route: {pl_traj_data['name']}")
    
    sectionizer = Sectionizer(ohl_traj, pl_traj)
    geometric_sections = sectionizer.discretize_and_section()

    # --- 2. Load Base Configurations ---
    print("\n--- 2. Loading System Configurations ---")
    # Load OHL config once
    with open(ohl_config_file, 'r') as f:
        ohl_config = json.load(f)
        print(f"OHL System: {ohl_config['system_parameters']['frequency']} Hz, "
              f"{ohl_config['system_parameters']['earth_resistivity']} Ω⋅m earth")
    
    # Load pipeline config once, but will modify its position for each section
    with open(pipeline_config_file, 'r') as f:
        pipeline_config = json.load(f)
        print(f"Pipeline: {pipeline_config['name']}")

    # Load currents
    with open(currents_file, 'r') as f:
        currents_str = json.load(f)
    currents = {c: {p: complex(v) for p, v in phases.items()} 
                for c, phases in currents_str.items() if c != 'description'}
    
    print(f"Operating Currents: {len(currents)} circuits loaded")

    # --- 3. Loop Through Sections and Calculate EMF ---
    print(f"\n--- 3. Electromagnetic Analysis ({len(geometric_sections)} sections) ---")
    total_induced_voltage = 0.0 + 0.0j  # Complex accumulator
    results = []

    for i, section in enumerate(geometric_sections):
        print(f"\nProcessing Section {i+1}/{len(geometric_sections)}...")
        print(f"  Length: {section['length_m']:.0f}m, Separation: {section['avg_separation_m']:.2f}m")
        
        # Update the pipeline's position for this specific section
        pipeline_config['position']['x_separation_m'] = section['avg_separation_m']
        
        # Create a temporary combined conductor list for this section's geometry
        all_conductors = []
        
        # Add OHL conductors
        ohl_conductor_types = ohl_config['conductor_types']
        for geo in ohl_config['tower_geometry']:
            ctype_props = ohl_conductor_types[geo['type']]
            all_conductors.append({
                'label': geo['conductor_id'], 
                'x': geo['x'], 
                'y': geo['y'],
                'gmr': ctype_props['gmr_impedance'], 
                'radius': ctype_props['gmr_potential'],
                'r_ac': ctype_props['r_ac'], 
                'type': 'earth' if geo['circuit_id'] is None else 'phase',
                'circuit_id': geo['circuit_id'], 
                'phase': geo['phase']
            })
            
        # Add pipeline conductor with updated position
        pl_props = pipeline_config['physical_properties']
        pl_pos = pipeline_config['position']
        pl_radius = pl_props['outer_diameter_m'] / 2.0
        pl_gmr = pl_radius
        pl_area = np.pi * (pl_radius**2 - (pl_radius - pl_props['steel_thickness_m'])**2)
        pl_r_dc = pl_props['steel_resistivity_ohmm'] / pl_area * 1000
        
        all_conductors.append({
            'label': 'Pipeline', 
            'x': pl_pos['x_separation_m'], 
            'y': -pl_pos['burial_depth_m'],
            'gmr': pl_gmr, 
            'radius': pl_radius, 
            'r_ac': pl_r_dc,
            'type': 'pipeline', 
            'circuit_id': 'PL1', 
            'phase': None
        })

        # Initialize the system for this section's geometry (suppress detailed output)
        print("  Calculating impedance matrix...", end="")
        
        # Temporarily redirect stdout to suppress detailed system output
        import sys
        from io import StringIO
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            system = MultiConductorSystem(
                conductors=all_conductors,
                frequency=ohl_config['system_parameters']['frequency'],
                earth_resistivity=ohl_config['system_parameters']['earth_resistivity']
            )
            
            # Calculate EMF per km
            emf_per_km = system.calculate_pipeline_emf(currents)
            
        finally:
            # Restore stdout
            sys.stdout = old_stdout
            
        print(" Done.")
        
        # Calculate total voltage for this section (V/km * km)
        section_voltage = emf_per_km * (section['length_m'] / 1000.0)
        
        results.append({
            'section': i + 1,
            'length_m': section['length_m'],
            'separation_m': section['avg_separation_m'],
            'emf_v_per_km': emf_per_km,
            'emf_magnitude_v_per_km': abs(emf_per_km),
            'section_voltage': section_voltage,
            'voltage_magnitude_v': abs(section_voltage)
        })
        
        # Add to total (vector sum)
        total_induced_voltage += section_voltage
        
        print(f"  → EMF = {abs(emf_per_km):.2f} V/km")
        print(f"  → Section Voltage = {abs(section_voltage):.2f} V")

    # --- 4. Final Results and Analysis ---
    print(f"\n{'='*60}")
    print("COMPREHENSIVE INTERFERENCE STUDY RESULTS")
    print(f"{'='*60}")
    
    print("\nSection-by-Section Analysis:")
    print("Section | Length (m) | Separation (m) | EMF (V/km) | Voltage (V)")
    print("-" * 65)
    
    total_length = 0
    for res in results:
        print(f"   {res['section']:2d}   |    {res['length_m']:4.0f}    |     {res['separation_m']:5.1f}     |   {res['emf_magnitude_v_per_km']:5.2f}    |   {res['voltage_magnitude_v']:6.2f}")
        total_length += res['length_m']
    
    print("-" * 65)
    print(f"TOTAL  |    {total_length:4.0f}    |       -       |     -      |   {abs(total_induced_voltage):6.2f}")
    
    # Summary statistics
    avg_emf = np.mean([r['emf_magnitude_v_per_km'] for r in results])
    max_emf = max([r['emf_magnitude_v_per_km'] for r in results])
    
    print(f"\nSummary Statistics:")
    print(f"  Total Pipeline Length: {total_length/1000:.2f} km")
    print(f"  Average EMF: {avg_emf:.2f} V/km")
    print(f"  Maximum EMF: {max_emf:.2f} V/km")
    print(f"  Total Longitudinal Induced Voltage: {abs(total_induced_voltage):.2f} V")
    print(f"  (Complex: {total_induced_voltage:.2f} V)")
    
    print(f"\nEngineering Assessment:")
    if abs(total_induced_voltage) > 100:
        print("  ⚠️  HIGH INTERFERENCE - Consider mitigation measures")
    elif abs(total_induced_voltage) > 50:
        print("  ⚡ MODERATE INTERFERENCE - Monitor and assess")
    else:
        print("  ✅ LOW INTERFERENCE - Within acceptable limits")
    
    print(f"\nNote: Results assume open-circuit conditions (no grounding)")
    print(f"Actual voltages will depend on pipeline grounding configuration.")
    
    return results, total_induced_voltage


if __name__ == '__main__':
    # Run the comprehensive study
    results, total_voltage = run_study(
        ohl_config_file='example_3_4_tower.json',
        pipeline_config_file='pipeline_config.json',
        ohl_traj_file='ohl_trajectory.json',
        pl_traj_file='pipeline_trajectory.json',
        currents_file='system_currents.json'
    )
    
    print(f"\n{'='*60}")
    print("STUDY COMPLETE")
    print(f"{'='*60}")
    print("✅ Geometric processing implemented")
    print("✅ Multi-section electromagnetic analysis completed") 
    print("✅ Vector summation of induced voltages calculated")
    print("✅ Professional interference assessment provided")
    print("\nReady for Phase 3: Advanced modeling and optimization")
