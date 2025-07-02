"""
longitudinal_analysis.py

Longitudinal voltage analysis using transmission line equations.
Implements the Telegrapher's equations for pipeline voltage profiles.
"""

import numpy as np
from scipy import constants
from pipeline import Pipeline

class LongitudinalAnalyzer:
    """
    Calculates longitudinal voltage and current profiles along pipeline sections
    using transmission line theory (Telegrapher's equations).
    """
    
    def __init__(self, pipeline_model):
        """
        Initialize with a Pipeline model.
        
        Args:
            pipeline_model (Pipeline): Advanced pipeline electrical model
        """
        self.pipeline = pipeline_model
        self.z = None
        self.y = None
        self.gamma = None
        self.Zc = None

    def initialize_electrical_parameters(self, use_textbook_values=True):
        """
        Initialize electrical parameters from pipeline model.
        
        Args:
            use_textbook_values (bool): Use textbook values for validation
        """
        self.z = self.pipeline.get_series_impedance(use_textbook_values)
        self.y = self.pipeline.get_shunt_admittance(use_textbook_values) 
        self.gamma, self.Zc = self.pipeline.calculate_propagation_parameters(use_textbook_values)

    def calculate_voltage_profile_uniform_emf(self, emf_per_km, length_km, 
                                            boundary_conditions='open'):
        """
        Calculate voltage profile for uniform EMF distribution.
        Ref: Equation (10.83a) and (10.83b)
        
        Args:
            emf_per_km (complex): Induced EMF per kilometer (V/km)
            length_km (float): Section length in kilometers
            boundary_conditions (str): 'open', 'grounded', or 'impedance'
            
        Returns:
            tuple: (x_points, voltage_profile, current_profile)
        """
        if self.gamma is None:
            self.initialize_electrical_parameters()

        print(f"\n--- Longitudinal Voltage Analysis ---")
        print(f"Section length: {length_km:.2f} km")
        print(f"Induced EMF: {abs(emf_per_km):.3f} V/km")
        print(f"Boundary conditions: {boundary_conditions}")

        # Distance points along the pipeline
        num_points = 101
        x_points = np.linspace(0, length_km, num_points)
        
        # For uniform EMF, the particular solution dominates
        # Simplified approach: assume EMF creates a uniform voltage rise
        
        if boundary_conditions == 'open':
            # Open circuit at both ends (worst case)
            # Voltage builds up linearly with distance
            voltage_profile = emf_per_km * x_points * (length_km - x_points) / length_km
            current_profile = np.zeros_like(voltage_profile, dtype=complex)
            
        elif boundary_conditions == 'grounded':
            # Grounded at both ends
            # Voltage follows sinh distribution
            gl = self.gamma * length_km
            voltage_profile = np.zeros(len(x_points), dtype=complex)
            current_profile = np.zeros(len(x_points), dtype=complex)
            
            for i, x in enumerate(x_points):
                gx = self.gamma * x
                # Transmission line solution with uniform driving function
                voltage_profile[i] = (emf_per_km / (self.gamma * self.z)) * \
                                   (np.sinh(gx) * np.sinh(gl - gx) / np.sinh(gl))
                current_profile[i] = voltage_profile[i] / self.Zc
                
        else:
            # Default to open circuit
            voltage_profile = emf_per_km * x_points * (length_km - x_points) / length_km
            current_profile = np.zeros_like(voltage_profile, dtype=complex)

        max_voltage = np.max(np.abs(voltage_profile))
        print(f"Maximum voltage: {max_voltage:.2f} V")
        
        return x_points, voltage_profile, current_profile

    def calculate_equivalent_circuit_voltage(self, emf_per_km, length_km):
        """
        Calculate total voltage using equivalent circuit approach.
        For short lines, this gives a good approximation.
        
        Args:
            emf_per_km (complex): Induced EMF per kilometer
            length_km (float): Section length
            
        Returns:
            complex: Total equivalent voltage
        """
        if self.z is None:
            self.initialize_electrical_parameters()

        # Total induced EMF for the section
        total_emf = emf_per_km * length_km
        
        # For a short line, voltage ≈ EMF (open circuit)
        # For longer lines or with loading, use transmission line equations
        
        if length_km < 1.0:  # Short line approximation
            equivalent_voltage = total_emf
        else:
            # Use transmission line correction
            gl = self.gamma * length_km
            correction_factor = np.sinh(gl) / gl if abs(gl) > 1e-6 else 1.0
            equivalent_voltage = total_emf * correction_factor
            
        return equivalent_voltage

    def analyze_section(self, emf_per_km, length_km, boundary_conditions='open'):
        """
        Complete analysis of a pipeline section.
        
        Args:
            emf_per_km (complex): Induced EMF per kilometer
            length_km (float): Section length
            boundary_conditions (str): Boundary condition type
            
        Returns:
            dict: Analysis results
        """
        x_points, V_profile, I_profile = self.calculate_voltage_profile_uniform_emf(
            emf_per_km, length_km, boundary_conditions)
        
        V_equivalent = self.calculate_equivalent_circuit_voltage(emf_per_km, length_km)
        
        results = {
            'length_km': length_km,
            'emf_per_km': emf_per_km,
            'boundary_conditions': boundary_conditions,
            'x_points': x_points,
            'voltage_profile': V_profile,
            'current_profile': I_profile,
            'max_voltage': np.max(np.abs(V_profile)),
            'equivalent_voltage': V_equivalent,
            'electrical_parameters': {
                'z': self.z,
                'y': self.y, 
                'gamma': self.gamma,
                'Zc': self.Zc
            }
        }
        
        return results


def validate_longitudinal_analysis():
    """
    Validate longitudinal analysis using Example 10.5 parameters.
    """
    print("=== LONGITUDINAL ANALYSIS VALIDATION ===")
    
    # Create pipeline from Example 10.5
    from pipeline import validate_example_10_5
    pipeline, z, y, gamma, Zc = validate_example_10_5()
    
    # Create analyzer
    analyzer = LongitudinalAnalyzer(pipeline)
    
    # Test with sample EMF (similar to our Phase 2 results)
    emf_per_km = 17.43 + 0j  # V/km (simplified to real for illustration)
    length_km = 1.0  # 1 km section
    
    # Analyze with different boundary conditions
    print(f"\n--- Open Circuit Analysis ---")
    results_open = analyzer.analyze_section(emf_per_km, length_km, 'open')
    
    print(f"\n--- Grounded Analysis ---") 
    results_grounded = analyzer.analyze_section(emf_per_km, length_km, 'grounded')
    
    print(f"\nComparison:")
    print(f"Open circuit max voltage: {results_open['max_voltage']:.2f} V")
    print(f"Grounded max voltage: {results_grounded['max_voltage']:.2f} V")
    print(f"Equivalent circuit voltage: {abs(results_open['equivalent_voltage']):.2f} V")
    
    return analyzer, results_open, results_grounded


if __name__ == '__main__':
    # Run validation
    analyzer, results_open, results_grounded = validate_longitudinal_analysis()
