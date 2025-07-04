#
# transmission_line_calculator.py
#
# A tool for calculating OHL parameters and pipeline interference.
# Based on the methods described in "Modelling of multi-conductor overhead lines and cables".
#

import numpy as np
from scipy import constants
import json

# --- Physical Constants ---
# Permittivity of free space (F/m)
EPSILON_0 = constants.epsilon_0
# Permeability of free space (H/m)
MU_0 = constants.mu_0

def load_system_from_json(ohl_filepath, pipeline_filepath):
    """
    Loads OHL and pipeline configurations and creates a single system.

    Args:
        ohl_filepath (str): The path to the OHL JSON configuration file.
        pipeline_filepath (str): The path to the pipeline JSON configuration file.

    Returns:
        tuple: A tuple containing (conductors_list, frequency, earth_resistivity).
    """
    # Load OHL config
    with open(ohl_filepath, 'r') as f:
        ohl_config = json.load(f)
    
    # Load Pipeline config
    with open(pipeline_filepath, 'r') as f:
        pl_config = json.load(f)

    # --- Build the combined conductor list ---
    all_conductors = []
    
    # 1. Add OHL conductors
    ohl_conductor_types = ohl_config['conductor_types']
    for geo in ohl_config['tower_geometry']:
        ctype_name = geo['type']
        ctype_props = ohl_conductor_types[ctype_name]
        conductor = {
            'label': geo['conductor_id'],
            'x': geo['x'], 
            'y': geo['y'],
            'gmr': ctype_props['gmr_impedance'],
            'radius': ctype_props['gmr_potential'],
            'r_ac': ctype_props['r_ac'],
            'type': 'earth' if geo['circuit_id'] is None else 'phase',
            'circuit_id': geo['circuit_id'], 
            'phase': geo['phase']
        }
        all_conductors.append(conductor)

    # 2. Add the Pipeline as another conductor
    pl_props = pl_config['physical_properties']
    pl_pos = pl_config['position']
    pl_radius = pl_props['outer_diameter_m'] / 2.0
    
    # For a solid steel pipe, GMR is approx r * e^(-mu_r/4), but for hollow it's more complex.
    # A common approximation for GMR of a steel pipe is simply its radius.
    pl_gmr = pl_radius 
    
    # AC resistance of the pipe (simplified, ignores skin effect in steel for now)
    pl_area = np.pi * (pl_radius**2 - (pl_radius - pl_props['steel_thickness_m'])**2)
    pl_r_dc = pl_props['steel_resistivity_ohmm'] / pl_area * 1000 # convert to ohm/km
    
    pipeline_conductor = {
        'label': 'Pipeline',
        'x': pl_pos['x_separation_m'], 
        'y': -pl_pos['burial_depth_m'], # y is negative for buried conductors
        'gmr': pl_gmr, 
        'radius': pl_radius, 
        'r_ac': pl_r_dc,
        'type': 'pipeline',
        'circuit_id': 'PL1', 
        'phase': None
    }
    all_conductors.append(pipeline_conductor)
    
    # Extract system parameters from OHL config
    params = ohl_config['system_parameters']
    freq = params['frequency']
    rho_earth = params['earth_resistivity']
        
    return all_conductors, freq, rho_earth

class MultiConductorSystem:
    """
    Represents a multi-conductor transmission system (OHL + Pipeline) and calculates its parameters.
    """
    def __init__(self, conductors, frequency, earth_resistivity):
        """
        Initializes the OverheadLine object.

        Args:
            conductors (list of dict): A list where each dict describes a conductor.
                Required keys: 'label' (str), 'x' (float, m), 'y' (float, m),
                               'gmr' (float, m), 'radius' (float, m),
                               'r_ac' (float, ohm/km), 'type' (str, 'phase' or 'earth').
            frequency (float): System frequency in Hz.
            earth_resistivity (float): Earth resistivity in Ohm-m.
        """
        self.conductors = conductors
        self.num_conductors = len(conductors)
        self.f = frequency
        self.omega = 2 * np.pi * self.f
        self.rho_earth = earth_resistivity

        # Identify indices for different conductor types
        self.phase_indices = [i for i, c in enumerate(self.conductors) if c['type'] == 'phase']
        self.earth_indices = [i for i, c in enumerate(self.conductors) if c['type'] == 'earth']
        self.pipeline_indices = [i for i, c in enumerate(self.conductors) if c['type'] == 'pipeline']

        # Pre-calculate distance matrices to avoid redundant calculations
        self._calculate_distance_matrices()

        print("--- System Configuration ---")
        print(f"Frequency: {self.f} Hz")
        print(f"Earth Resistivity: {self.rho_earth} Ohm-m")
        print(f"Number of conductors: {self.num_conductors}")
        for i, c in enumerate(self.conductors):
            print(f"  Conductor {i+1} ({c['label']}): x={c['x']:.2f}m, y={c['y']:.2f}m, type={c['type']}")
        print("-" * 28 + "\n")


    def _calculate_distance_matrices(self):
        """
        Calculates the matrices of distances between conductors and their images.
        """
        self.d_matrix = np.zeros((self.num_conductors, self.num_conductors))
        self.D_matrix = np.zeros((self.num_conductors, self.num_conductors))

        for i in range(self.num_conductors):
            for j in range(self.num_conductors):
                cond_i = self.conductors[i]
                cond_j = self.conductors[j]
                dx = cond_i['x'] - cond_j['x']
                dy_same = cond_i['y'] - cond_j['y']
                dy_image = cond_i['y'] + cond_j['y']
                self.d_matrix[i, j] = np.sqrt(dx**2 + dy_same**2)
                self.D_matrix[i, j] = np.sqrt(dx**2 + dy_image**2)

    def calculate_potential_matrix(self):
        """
        Calculates Maxwell's Potential Coefficient Matrix (P) in km/uF.
        Ref: Equations (3.2a) and (3.2b), page 5.
        """
        P_matrix = np.zeros((self.num_conductors, self.num_conductors))
        const = 1 / (2 * np.pi * EPSILON_0) * 1e-9 # Gives km/uF

        for i in range(self.num_conductors):
            for j in range(self.num_conductors):
                if i == j:
                    y_i = self.conductors[i]['y']
                    r_i = self.conductors[i]['radius']
                    # For buried conductors (negative y), use absolute value for the image method
                    if y_i < 0:
                        P_matrix[i, j] = const * np.log(2 * abs(y_i) / r_i)
                    else:
                        P_matrix[i, j] = const * np.log(2 * y_i / r_i)
                else:
                    D_ij = self.D_matrix[i, j]
                    d_ij = self.d_matrix[i, j]
                    P_matrix[i, j] = const * np.log(D_ij / d_ij)

        self.P_matrix = P_matrix
        return self.P_matrix

    def calculate_capacitance_matrix(self):
        """
        Calculates the Shunt Capacitance Matrix (C) in uF/km.
        Ref: Equation (3.3c), page 5. C = P^-1
        """
        if not hasattr(self, 'P_matrix'):
            self.calculate_potential_matrix()
        self.C_matrix = np.linalg.inv(self.P_matrix)
        return self.C_matrix

    def reduce_matrix_by_elimination(self, M, keep_indices, elim_indices):
        """
        Reduces a matrix using Kron reduction.

        Args:
            M (np.array): The full square matrix to reduce.
            keep_indices (list): A list of indices to keep.
            elim_indices (list): A list of indices to eliminate.

        Returns:
            np.array: The reduced matrix.
        """
        M_aa = M[np.ix_(keep_indices, keep_indices)]
        M_ab = M[np.ix_(keep_indices, elim_indices)]
        M_ba = M[np.ix_(elim_indices, keep_indices)]
        M_bb = M[np.ix_(elim_indices, elim_indices)]

        M_bb_inv = np.linalg.inv(M_bb)
        
        # For potential matrix, use special formula: P_reduced = P_aa - P_ab @ inv(P_bb) @ P_ba
        # Then C_reduced = inv(P_reduced). Let's follow the book.
        if hasattr(self, 'P_matrix') and M is self.P_matrix:
            P_reduced = M_aa - M_ab @ M_bb_inv @ M_ba
            return np.linalg.inv(P_reduced)
        # For impedance and other matrices, use standard formula: M_reduced = M_aa - M_ab @ inv(M_bb) @ M_ba
        else:
            return M_aa - M_ab @ M_bb_inv @ M_ba

    def calculate_series_impedance_matrix(self):
        """
        Calculates the Series Impedance Matrix (Z) in Ohm/km.
        Ref: Equations (3.19a) and (3.20a), page 11.
        """
        # Depth of equivalent earth return conductor, Eq (3.15)
        D_erc = 658.87 * np.sqrt(self.rho_earth / self.f)
        print(f"Depth of equivalent earth return conductor D_erc = {D_erc:.1f} m")

        Z_matrix = np.zeros((self.num_conductors, self.num_conductors), dtype=complex)
        
        # Earth return resistance term (same for all elements)
        R_earth = np.pi**2 * self.f * 1e-4 # Ohm/km
        
        # Reactance constant
        X_const = self.omega * MU_0 / (2 * np.pi) * 1e3 # Converts H/m to Ohm/km

        for i in range(self.num_conductors):
            for j in range(self.num_conductors):
                if i == j:
                    # Self-Impedance Z_ii, Eq (3.19a)
                    r_ac_i = self.conductors[i]['r_ac']
                    gmr_i = self.conductors[i]['gmr']
                    Z_matrix[i, j] = (r_ac_i + R_earth) + 1j * X_const * np.log(D_erc / gmr_i)
                else:
                    # Mutual-Impedance Z_ij, Eq (3.20a)
                    d_ij = self.d_matrix[i, j]
                    Z_matrix[i, j] = R_earth + 1j * X_const * np.log(D_erc / d_ij)
        
        self.Z_matrix = Z_matrix
        return self.Z_matrix

    def calculate_transposed_matrices(self):
        """
        Calculates the balanced phase impedance and susceptance matrices for a
        perfectly transposed 3-phase line.

        This method averages the diagonal and off-diagonal elements of the
        untransposed 3x3 phase matrices.
        Ref: Eq (3.43c) for Impedance and (3.53b) for Susceptance.
        """
        if not hasattr(self, 'Z_phase_untransposed'):
            print("Calculating untransposed matrices first...")
            # Calculate full Z matrix
            Z_full = self.calculate_series_impedance_matrix()
            # Reduce to get untransposed phase impedance matrix
            self.Z_phase_untransposed = self.reduce_matrix_by_elimination(
                Z_full, self.phase_indices, self.earth_indices)

            # Calculate full P matrix and reduce to get untransposed phase capacitance
            P_full = self.calculate_potential_matrix()
            self.C_phase_untransposed = self.reduce_matrix_by_elimination(
                P_full, self.phase_indices, self.earth_indices)

        # --- Transposed Impedance Matrix ---
        Z_un = self.Z_phase_untransposed
        z_s = np.mean(np.diag(Z_un))
        # Average the off-diagonal elements (assuming symmetry)
        z_m = (Z_un[0,1] + Z_un[0,2] + Z_un[1,2]) / 3.0
        
        self.Z_phase_transposed = np.full((3, 3), z_m, dtype=complex)
        np.fill_diagonal(self.Z_phase_transposed, z_s)

        # --- FINAL CORRECTED Transposed Susceptance Matrix ---
        # To match the textbook's method, the averaging is done on the
        # elements of the B = omega * C matrix (Maxwell form), NOT the nodal form.
        
        # 1. Get the reduced 3x3 phase capacitance matrix (Maxwell form)
        C_phase_un = self.C_phase_untransposed # uF/km
        
        # 2. Calculate the intermediate B matrix (B = wC)
        B_intermediate = self.omega * C_phase_un # uS/km

        # 3. Average the elements of this intermediate matrix (Ref: Eq 3.53b)
        B_self_avg = np.mean(np.diag(B_intermediate))
        # Off-diagonals of Maxwell C are negative, so B_mutual will be negative
        B_mutual_avg = (B_intermediate[0,1] + B_intermediate[0,2] + B_intermediate[1,2]) / 3.0
        
        # 4. Construct the final balanced nodal admittance matrix
        # The textbook on p59 uses B_s = B_Self and B_m = B_Mutual
        # The final matrix structure has B_s on diagonal and B_m on off-diagonals
        # Since B_mutual_avg is already negative from the Maxwell form, use it directly
        
        self.B_phase_transposed = np.full((3, 3), B_mutual_avg)
        np.fill_diagonal(self.B_phase_transposed, B_self_avg)

        return self.Z_phase_transposed, self.B_phase_transposed

    def calculate_sequence_matrices(self):
        """
        Calculates the sequence impedance and susceptance matrices (Z_PNZ, B_PNZ)
        from the balanced transposed phase matrices. The output is ordered
        [Positive, Negative, Zero].
        """
        if not hasattr(self, 'Z_phase_transposed'):
            print("Calculating transposed matrices first...")
            self.calculate_transposed_matrices()

        # Define the 'a' operator
        a = np.exp(1j * 2 * np.pi / 3)

        # Define the Fortescue transformation matrix H for a P-N-Z output order
        H = np.array([
            [1, 1, 1],
            [a**2, a, 1],
            [a, a**2, 1]
        ])
        
        # Calculate the inverse of H
        H_inv = np.linalg.inv(H)

        # --- Sequence Impedance Matrix ---
        # Z_PNZ = H_inv @ Z_phase_transposed @ H
        self.Z_PNZ = H_inv @ self.Z_phase_transposed @ H

        # --- Sequence Susceptance Matrix ---
        # B_PNZ = H_inv @ B_phase_transposed @ H
        self.B_PNZ = H_inv @ self.B_phase_transposed @ H
        
        return self.Z_PNZ, self.B_PNZ

    def calculate_pipeline_emf(self, ohl_currents):
        """
        Calculates the induced longitudinal EMF on the pipeline per km.
        Ref: Equation (10.76)

        Args:
            ohl_currents (dict): A dict with circuit and phase currents.

        Returns:
            complex: The induced EMF in Volts/km.
        """
        if not hasattr(self, 'Z_matrix'):
            self.calculate_series_impedance_matrix()
        
        # 1. Create a current vector in the correct order of the phase conductors
        I_vector = np.zeros(len(self.phase_indices), dtype=complex)
        for i, cond_idx in enumerate(self.phase_indices):
            cond = self.conductors[cond_idx]
            I_vector[i] = ohl_currents[cond['circuit_id']][cond['phase']]

        # 2. Get the mutual impedances between the pipeline and all OHL phase conductors
        # Z_mutual will be a row vector
        pipeline_idx = self.pipeline_indices[0] # Assuming one pipeline
        Z_mutual_pipeline_phases = self.Z_matrix[pipeline_idx, self.phase_indices]

        # 3. Get the mutual impedances between the pipeline and all earth wires
        Z_mutual_pipeline_earth = self.Z_matrix[pipeline_idx, self.earth_indices]

        # 4. Calculate the induced current in the earth wires
        # From Eq (10.76), I_e = -inv(Z_ee) @ Z_ep @ I_p
        Z_ee = self.Z_matrix[np.ix_(self.earth_indices, self.earth_indices)]
        Z_ep = self.Z_matrix[np.ix_(self.earth_indices, self.phase_indices)]
        
        I_earth_wires = -np.linalg.inv(Z_ee) @ Z_ep @ I_vector

        # 5. Calculate total EMF from phases and earth wires
        # EMF = Z_pP * I_P + Z_pE * I_E
        emf_from_phases = np.dot(Z_mutual_pipeline_phases, I_vector)
        emf_from_earth_wires = np.dot(Z_mutual_pipeline_earth, I_earth_wires)

        total_emf = emf_from_phases + emf_from_earth_wires
        return total_emf # V/km

    def calculate_fault_emf(self, fault_current, faulted_phase_label='A'):
        """
        Calculates the induced EMF during a single-phase-to-ground fault.
        Ref: Equation (10.79)
        
        Args:
            fault_current (complex): The fault current in Amps.
            faulted_phase_label (str): The phase label ('A', 'B', or 'C').
            
        Returns:
            complex: The induced EMF in Volts/km.
        """
        if not hasattr(self, 'Z_matrix'):
            self.calculate_series_impedance_matrix()
            
        print(f"\n--- Fault EMF Analysis ---")
        print(f"Fault current: {abs(fault_current):.0f} A")
        print(f"Faulted phase: {faulted_phase_label}")
            
        # Find indices for faulted phase and pipeline
        faulted_phase_idx = None
        for i, c in enumerate(self.conductors):
            if c.get('phase') == faulted_phase_label:
                faulted_phase_idx = i
                break
                
        if faulted_phase_idx is None:
            print(f"Error: Phase {faulted_phase_label} not found")
            return 0 + 0j
            
        pipeline_idx = self.pipeline_indices[0]
        
        # Get relevant impedances from the full Z matrix
        Z_pp = self.Z_matrix[faulted_phase_idx, pipeline_idx]  # Mutual between faulted phase and pipeline
        
        # Calculate screening factor k (simplified approach)
        if self.earth_indices:
            # With earth wire - calculate detailed screening factor
            Z_ep = self.Z_matrix[np.ix_(self.earth_indices, [faulted_phase_idx])].flatten()
            Z_ee = self.Z_matrix[np.ix_(self.earth_indices, self.earth_indices)]
            Z_pe = self.Z_matrix[pipeline_idx, self.earth_indices]
            
            # Screening factor k, Ref Eq (10.79b)
            if len(self.earth_indices) == 1:
                shielding_term = Z_pe * Z_ep / Z_ee[0,0]
            else:
                shielding_term = np.dot(Z_pe, np.linalg.inv(Z_ee)).dot(Z_ep)
            k = 1 - (shielding_term / Z_pp)
        else:
            # No earth wire - minimal screening
            k = 1.0 + 0j
        
        # Induced EMF, Ref Eq (10.79a)
        emf = -Z_pp * k * fault_current
        
        print(f"Mutual impedance Z_pp: {Z_pp:.4f} Ω/km")
        print(f"Screening factor k: {k:.4f}")
        print(f"Fault EMF: {abs(emf):.1f} V/km")
        
        return emf

# --- Main execution block ---
if __name__ == '__main__':
    print("Executing Transmission Line Parameter Calculator with Pipeline Interference...\n")

    # --- 1. Load System Configuration ---
    ohl_file = 'example_3_4_tower.json'
    pipeline_file = 'pipeline_config.json'
    conductors, freq, rho_earth = load_system_from_json(ohl_file, pipeline_file)
    
    with open('system_currents.json', 'r') as f:
        currents_str = json.load(f)
    # Convert string currents to complex numbers
    currents = {c: {p: complex(v) for p, v in phases.items()} 
                for c, phases in currents_str.items() if c != 'description'}

    # --- 2. Initialize and Analyze the System ---
    system = MultiConductorSystem(conductors, freq, rho_earth)
    
    # --- 3. Calculate Basic Matrices ---
    print("\n--- 1. Calculating Combined System Matrices ---")
    Z_full = system.calculate_series_impedance_matrix()
    P_full = system.calculate_potential_matrix()
    C_full = np.linalg.inv(P_full)
    
    # --- 4. Calculate Inductive Coupling (EMF) ---
    print("\n--- 2. Calculating Inductive Coupling ---")
    induced_emf = system.calculate_pipeline_emf(currents)
    
    print(f"\nLongitudinal Induced EMF on Pipeline: {abs(induced_emf):.3f} V/km")
    print(f"(Complex value: {induced_emf:.3f} V/km)")
    
    # --- 5. Display System Configuration ---
    print("\n--- 3. Combined System Analysis Results ---")
    np.set_printoptions(precision=4, suppress=True)
    
    print(f"\nCombined {system.num_conductors}x{system.num_conductors} Series Impedance Matrix Z (Ohm/km):")
    print("(Last row/column represents pipeline mutual impedances)")
    print(Z_full)
    
    # Show pipeline-specific mutual impedances
    if system.pipeline_indices:
        pipeline_idx = system.pipeline_indices[0]
        print(f"\nPipeline Self-Impedance: {Z_full[pipeline_idx, pipeline_idx]:.4f} Ω/km")
        print("Pipeline Mutual Impedances with OHL phases:")
        for i, phase_idx in enumerate(system.phase_indices):
            phase_label = system.conductors[phase_idx]['label']
            mutual_z = Z_full[pipeline_idx, phase_idx]
            print(f"  Z_pipeline-{phase_label}: {mutual_z:.4f} Ω/km")

    print("\n--- Analysis Complete ---")
    print("✓ OHL and Pipeline models integrated.")
    print("✓ Mutual impedance matrix calculated for the combined system.")
    print("✓ Induced EMF calculation implemented, including earth wire shielding.")
    print("✓ Ready for geometric sectionization and longitudinal voltage analysis.")