"""
fault_analysis.py

Fault condition analysis for pipeline interference studies.
Implements screening factor calculations and fault-induced EMF analysis.
"""

import numpy as np
from scipy import constants

class FaultAnalyzer:
    """
    Analyzes pipeline interference under fault conditions.
    Implements screening factor calculations and fault-induced EMF.
    """
    
    def __init__(self, multi_conductor_system):
        """
        Initialize with a MultiConductorSystem.
        
        Args:
            multi_conductor_system: The combined OHL+pipeline system
        """
        self.system = multi_conductor_system
        if not hasattr(self.system, 'Z_matrix'):
            # Ensure the full impedance matrix is calculated once
            self.system.calculate_series_impedance_matrix()

    def calculate_screening_factor(self, faulted_phase_label):
        """
        Calculate the screening factor k for a fault on a specific phase.
        Ref: Equation (10.79b)

        Args:
            faulted_phase_label (str): The label of the faulted phase conductor 
                                       (e.g., 'R', 'Y', 'B').
            
        Returns:
            complex: The calculated screening factor k.
        """
        print(f"\n--- Screening Factor Analysis for fault on '{faulted_phase_label}' ---")

        # Ensure impedance matrix is calculated
        if not hasattr(self.system, 'Z_matrix'):
            self.system.calculate_series_impedance_matrix()

        # Find indices from the system configuration
        try:
            faulted_phase_idx = [i for i, c in enumerate(self.system.conductors) if c['label'] == faulted_phase_label][0]
        except IndexError:
            raise ValueError(f"Faulted phase '{faulted_phase_label}' not found in the system configuration.")
            
        pipeline_idx = self.system.pipeline_indices[0]
        earth_indices = self.system.earth_indices
        
        if not earth_indices:
            print("No earth wires found. Screening factor k = 1.0 (no shielding).")
            return 1.0 + 0.0j

        # Get relevant sub-matrices from the full Z matrix
        # Z_ep: Mutual impedance between earth wires and the faulted phase
        Z_ep = self.system.Z_matrix[np.ix_(earth_indices, [faulted_phase_idx])]
        
        # Z_ee: Self and mutual impedances of the earth wires
        Z_ee = self.system.Z_matrix[np.ix_(earth_indices, earth_indices)]
        
        # Z_pe: Mutual impedance between the pipeline and the earth wires
        Z_pe = self.system.Z_matrix[np.ix_([pipeline_idx], earth_indices)]
        
        # Z_pp: Mutual impedance between the faulted phase and the pipeline
        Z_pp_mutual = self.system.Z_matrix[faulted_phase_idx, pipeline_idx]
        
        # Calculate the shielding term: Z_pe * inv(Z_ee) * Z_ep
        # This represents the voltage induced on the pipeline by the earth wire currents
        shielding_term = (Z_pe @ np.linalg.inv(Z_ee) @ Z_ep)[0, 0] # Result is a 1x1 matrix
        
        # Calculate screening factor k
        k = 1 - (shielding_term / Z_pp_mutual)
        
        print(f"Calculated Screening Factor (k): {k:.4f} ({abs(k):.4f} ∠ {np.angle(k, deg=True):.1f}°)")
        
        return k

    def calculate_fault_emf(self, fault_current, faulted_phase_label):
        """
        Calculate induced EMF during a fault on a specific phase.
        Ref: Equation (10.79a)
        
        Args:
            fault_current (complex): Fault current in Amperes.
            faulted_phase_label (str): The label of the faulted phase conductor.
            
        Returns:
            complex: Induced EMF per kilometer during the fault (V/km).
        """
        print(f"\n--- Fault EMF Analysis ---")
        print(f"Fault on phase '{faulted_phase_label}' with current {abs(fault_current):.0f} A")

        # Calculate the precise screening factor for this fault
        k = self.calculate_screening_factor(faulted_phase_label)
        
        # Get the direct mutual impedance between the faulted phase and the pipeline
        faulted_phase_idx = [i for i, c in enumerate(self.system.conductors) if c['label'] == faulted_phase_label][0]
        pipeline_idx = self.system.pipeline_indices[0]
        Z_mutual_direct = self.system.Z_matrix[faulted_phase_idx, pipeline_idx]
        
        # Fault-induced EMF = -Z_mutual * k * I_fault
        # The negative sign is because EMF opposes the change in flux.
        emf_fault = -Z_mutual_direct * k * fault_current
        
        print(f"Direct Mutual Impedance Z_mp = {Z_mutual_direct:.4f} Ω/km")
        print(f"Net Fault-induced EMF: {abs(emf_fault):.2f} V/km (Complex: {emf_fault:.2f} V/km)")
        
        return emf_fault

    def analyze_touch_voltage_risk(self, induced_voltage, pipeline_grounding_resistance=10):
        """
        Analyze touch voltage risk from induced voltages.
        
        Args:
            induced_voltage (complex): Total induced voltage in pipeline
            pipeline_grounding_resistance (float): Grounding resistance in Ohms
            
        Returns:
            dict: Touch voltage analysis results
        """
        print(f"\n--- Touch Voltage Risk Analysis ---")
        print(f"Induced voltage: {abs(induced_voltage):.2f} V")
        print(f"Grounding resistance: {pipeline_grounding_resistance:.1f} Ω")

        # Touch voltage depends on grounding configuration
        # For well-grounded pipeline, touch voltage is much lower than induced voltage
        touch_voltage = abs(induced_voltage) * 0.1  # Simplified estimate
        
        # Safety thresholds (typical values)
        safe_threshold = 50  # V
        dangerous_threshold = 100  # V
        
        risk_level = "LOW"
        if touch_voltage > dangerous_threshold:
            risk_level = "HIGH"
        elif touch_voltage > safe_threshold:
            risk_level = "MODERATE"
            
        results = {
            'induced_voltage': abs(induced_voltage),
            'touch_voltage_estimate': touch_voltage,
            'grounding_resistance': pipeline_grounding_resistance,
            'risk_level': risk_level,
            'safe_threshold': safe_threshold,
            'dangerous_threshold': dangerous_threshold
        }
        
        print(f"Estimated touch voltage: {touch_voltage:.1f} V")
        print(f"Risk level: {risk_level}")
        
        return results

    def comprehensive_fault_study(self, fault_scenarios):
        """
        Perform comprehensive fault analysis for multiple scenarios.
        
        Args:
            fault_scenarios (list): List of fault scenario dictionaries
            
        Returns:
            list: Results for each scenario
        """
        print(f"\n{'='*60}")
        print("COMPREHENSIVE FAULT ANALYSIS")
        print(f"{'='*60}")
        
        results = []
        
        for i, scenario in enumerate(fault_scenarios):
            print(f"\n--- Scenario {i+1}: {scenario['description']} ---")
            
            # Calculate fault EMF
            faulted_phase_label = scenario.get('faulted_phase_label', 'R')  # Default to phase R
            emf_fault = self.calculate_fault_emf(
                fault_current=scenario['fault_current'],
                faulted_phase_label=faulted_phase_label
            )
            
            # Estimate total voltage for a representative length
            section_length = scenario.get('section_length', 1.0)  # km
            total_voltage = emf_fault * section_length
            
            # Touch voltage analysis
            touch_analysis = self.analyze_touch_voltage_risk(
                total_voltage, 
                scenario.get('grounding_resistance', 10)
            )
            
            scenario_results = {
                'scenario': scenario,
                'emf_per_km': emf_fault,
                'total_voltage': total_voltage,
                'touch_analysis': touch_analysis
            }
            
            results.append(scenario_results)
            
            print(f"Summary: EMF={abs(emf_fault):.1f} V/km, "
                  f"Total={abs(total_voltage):.1f} V, "
                  f"Risk={touch_analysis['risk_level']}")
        
        return results


def create_example_fault_scenarios():
    """
    Create example fault scenarios for testing.
    
    Returns:
        list: Example fault scenarios
    """
    scenarios = [
        {
            'description': 'Single-phase ground fault (close)',
            'fault_type': 'single_phase_ground',
            'faulted_phase_label': 'R',
            'fault_current': 5000 + 0j,  # A
            'fault_duration': 0.1,  # s
            'distance_to_fault': 0.5,  # km
            'section_length': 1.0,  # km
            'grounding_resistance': 10  # Ω
        },
        {
            'description': 'Single-phase ground fault (distant)',
            'fault_type': 'single_phase_ground',
            'faulted_phase_label': 'Y', 
            'fault_current': 3000 + 0j,  # A
            'fault_duration': 0.2,  # s
            'distance_to_fault': 5.0,  # km
            'section_length': 1.0,  # km
            'grounding_resistance': 10  # Ω
        },
        {
            'description': 'Three-phase fault',
            'fault_type': 'three_phase',
            'faulted_phase_label': 'B',
            'fault_current': 8000 + 0j,  # A
            'fault_duration': 0.05,  # s
            'distance_to_fault': 1.0,  # km
            'section_length': 1.0,  # km
            'grounding_resistance': 10  # Ω
        }
    ]
    
    return scenarios


def validate_fault_analysis():
    """
    Validate fault analysis using our existing system.
    """
    print("=== FAULT ANALYSIS VALIDATION ===")
    
    # Import and create our existing system
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from transmission_line_calculator import MultiConductorSystem, load_system_from_json
    
    # Load system
    conductors, freq, rho_earth = load_system_from_json(
        'example_3_4_tower.json', 'pipeline_config.json')
    
    # Suppress system output for clean fault analysis
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    
    try:
        system = MultiConductorSystem(conductors, freq, rho_earth)
    finally:
        sys.stdout = old_stdout
    
    # Create fault analyzer
    fault_analyzer = FaultAnalyzer(system)
    
    # Run comprehensive fault study
    scenarios = create_example_fault_scenarios()
    results = fault_analyzer.comprehensive_fault_study(scenarios)
    
    print(f"\n✅ Fault analysis validation complete")
    print(f"Analyzed {len(scenarios)} fault scenarios")
    
    return fault_analyzer, results


if __name__ == '__main__':
    # Run validation
    fault_analyzer, results = validate_fault_analysis()
