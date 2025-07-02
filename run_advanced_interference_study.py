"""
run_advanced_interference_study.py

Comprehensive Phase 3 interference analysis with advanced modeling.
Integrates pipeline electrical modeling, longitudinal analysis, and fault studies.
"""

import json
import numpy as np
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from transmission_line_calculator import MultiConductorSystem, load_system_from_json
from geometry_processor import Sectionizer
from pipeline import Pipeline
from longitudinal_analysis import LongitudinalAnalyzer
from fault_analysis import FaultAnalyzer, create_example_fault_scenarios

def run_advanced_study():
    """
    Run comprehensive Phase 3 interference study with advanced modeling.
    """
    print("=" * 70)
    print("COMPREHENSIVE PIPELINE INTERFERENCE STUDY - PHASE 3")
    print("Advanced Modeling: Pipeline Electrical + Longitudinal + Fault Analysis")
    print("=" * 70)

    # --- 1. Load Basic System Configuration ---
    print("\n--- 1. Loading System Configuration ---")
    ohl_file = 'example_3_4_tower.json'
    pipeline_file = 'pipeline_config.json'
    currents_file = 'system_currents.json'
    
    # Load configurations
    with open(ohl_file, 'r') as f:
        ohl_config = json.load(f)
    with open(pipeline_file, 'r') as f:
        pipeline_config = json.load(f)
    with open(currents_file, 'r') as f:
        currents_str = json.load(f)
    
    # Convert currents
    currents = {c: {p: complex(v) for p, v in phases.items()} 
                for c, phases in currents_str.items() if c != 'description'}
    
    frequency = ohl_config['system_parameters']['frequency']
    earth_resistivity = ohl_config['system_parameters']['earth_resistivity']
    
    print(f"OHL System: {frequency} Hz, {earth_resistivity} Ω⋅m earth")
    print(f"Pipeline: {pipeline_config['name']}")
    print(f"Operating Currents: {len(currents)} circuits loaded")

    # --- 2. Advanced Pipeline Electrical Modeling ---
    print(f"\n--- 2. Advanced Pipeline Electrical Modeling ---")
    
    # Create advanced pipeline model
    advanced_pipeline = Pipeline(pipeline_config, frequency, earth_resistivity)
    
    # Calculate detailed electrical parameters
    z_pipeline = advanced_pipeline.get_series_impedance(use_textbook_values=True)
    y_pipeline = advanced_pipeline.get_shunt_admittance(use_textbook_values=True)
    gamma, Zc = advanced_pipeline.calculate_propagation_parameters(use_textbook_values=True)

    # --- 3. Basic EMF Calculation (from Phase 2) ---
    print(f"\n--- 3. Basic EMF Calculation ---")
    
    # Load system for EMF calculation (suppress output)
    old_stdout = sys.stdout
    from io import StringIO
    sys.stdout = StringIO()
    
    try:
        conductors, freq, rho_earth = load_system_from_json(ohl_file, pipeline_file)
        system = MultiConductorSystem(conductors, freq, rho_earth)
        basic_emf = system.calculate_pipeline_emf(currents)
    finally:
        sys.stdout = old_stdout
    
    print(f"Basic induced EMF: {abs(basic_emf):.3f} V/km")
    print(f"(Complex: {basic_emf:.3f} V/km)")

    # --- 4. Longitudinal Voltage Analysis ---
    print(f"\n--- 4. Longitudinal Voltage Analysis ---")
    
    # Create longitudinal analyzer
    long_analyzer = LongitudinalAnalyzer(advanced_pipeline)
    
    # Analyze different section lengths and boundary conditions
    test_lengths = [0.5, 1.0, 2.0]  # km
    boundary_conditions = ['open', 'grounded']
    
    longitudinal_results = {}
    
    for length in test_lengths:
        for bc in boundary_conditions:
            key = f"{length}km_{bc}"
            print(f"\nAnalyzing {length} km section ({bc} circuit):")
            
            results = long_analyzer.analyze_section(basic_emf, length, bc)
            longitudinal_results[key] = results
            
            print(f"  Max voltage: {results['max_voltage']:.2f} V")
            print(f"  Equivalent voltage: {abs(results['equivalent_voltage']):.2f} V")

    # --- 5. Fault Analysis ---
    print(f"\n--- 5. Fault Analysis ---")
    
    # Create fault analyzer
    fault_analyzer = FaultAnalyzer(system)
    
    # Run comprehensive fault study
    fault_scenarios = create_example_fault_scenarios()
    fault_results = fault_analyzer.comprehensive_fault_study(fault_scenarios)

    # --- 6. Comprehensive Results Summary ---
    print(f"\n{'='*70}")
    print("COMPREHENSIVE RESULTS SUMMARY")
    print(f"{'='*70}")
    
    print(f"\n📊 PIPELINE ELECTRICAL PARAMETERS:")
    print(f"  Series impedance (z): {z_pipeline:.5f} Ω/km")
    print(f"  Shunt admittance (y): {y_pipeline:.5f} S/km") 
    print(f"  Propagation constant (γ): {gamma:.6f} /km")
    print(f"  Characteristic impedance (Zc): {abs(Zc):.1f} Ω")
    
    print(f"\n⚡ STEADY-STATE INTERFERENCE:")
    print(f"  Basic EMF: {abs(basic_emf):.3f} V/km")
    
    print(f"\n📏 LONGITUDINAL VOLTAGE ANALYSIS:")
    for key, results in longitudinal_results.items():
        length = results['length_km']
        bc = results['boundary_conditions']
        max_v = results['max_voltage']
        equiv_v = abs(results['equivalent_voltage'])
        print(f"  {length} km ({bc}): Max = {max_v:.1f} V, Equiv = {equiv_v:.1f} V")
    
    print(f"\n⚠️  FAULT CONDITION ANALYSIS:")
    for i, result in enumerate(fault_results):
        scenario = result['scenario']
        emf = abs(result['emf_per_km'])
        total_v = abs(result['total_voltage'])
        risk = result['touch_analysis']['risk_level']
        print(f"  Scenario {i+1} ({scenario['fault_type']}): "
              f"EMF = {emf:.1f} V/km, Total = {total_v:.1f} V, Risk = {risk}")

    # --- 7. Engineering Assessment ---
    print(f"\n🔍 ENGINEERING ASSESSMENT:")
    
    # Steady-state assessment
    max_steady_state = max([r['max_voltage'] for r in longitudinal_results.values()])
    if max_steady_state > 100:
        ss_assessment = "HIGH - Mitigation required"
    elif max_steady_state > 50:
        ss_assessment = "MODERATE - Monitor closely"
    else:
        ss_assessment = "ACCEPTABLE - Standard precautions"
    
    print(f"  Steady-state risk: {ss_assessment}")
    print(f"  Maximum steady-state voltage: {max_steady_state:.1f} V")
    
    # Fault assessment
    max_fault_voltage = max([abs(r['total_voltage']) for r in fault_results])
    high_risk_faults = sum([1 for r in fault_results 
                           if r['touch_analysis']['risk_level'] == 'HIGH'])
    
    print(f"  Maximum fault voltage: {max_fault_voltage:.1f} V")
    print(f"  High-risk fault scenarios: {high_risk_faults}/{len(fault_results)}")
    
    # Overall recommendation
    if high_risk_faults > 0 or max_steady_state > 100:
        overall = "MITIGATION REQUIRED"
        print(f"  ❌ Overall assessment: {overall}")
        print(f"     Recommend: Increased separation, grounding improvements,")
        print(f"                or pipeline route modification")
    elif max_steady_state > 50 or max_fault_voltage > 200:
        overall = "ENHANCED MONITORING"
        print(f"  ⚠️  Overall assessment: {overall}")
        print(f"     Recommend: Regular monitoring, touch voltage testing")
    else:
        overall = "ACCEPTABLE"
        print(f"  ✅ Overall assessment: {overall}")
        print(f"     Standard safety precautions sufficient")

    # --- 8. Return Results ---
    comprehensive_results = {
        'pipeline_parameters': {
            'z': z_pipeline,
            'y': y_pipeline,
            'gamma': gamma,
            'Zc': Zc
        },
        'basic_emf': basic_emf,
        'longitudinal_results': longitudinal_results,
        'fault_results': fault_results,
        'assessment': {
            'max_steady_state_voltage': max_steady_state,
            'max_fault_voltage': max_fault_voltage,
            'high_risk_fault_count': high_risk_faults,
            'steady_state_assessment': ss_assessment,
            'overall_recommendation': overall
        }
    }
    
    print(f"\n{'='*70}")
    print("PHASE 3 ADVANCED ANALYSIS COMPLETE")
    print(f"{'='*70}")
    print("✅ Advanced pipeline electrical modeling implemented")
    print("✅ Longitudinal voltage analysis completed")
    print("✅ Comprehensive fault analysis performed")
    print("✅ Professional engineering assessment provided")
    print("\nReady for Example 10.5 validation and production deployment")
    
    return comprehensive_results


if __name__ == '__main__':
    # Run the comprehensive advanced study
    results = run_advanced_study()
