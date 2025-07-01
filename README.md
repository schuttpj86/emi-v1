# EMI Analysis Tool v1

A professional-grade Python tool for calculating overhead transmission line parameters and electromagnetic interference (EMI) analysis. This tool implements Carson-Clem equations for multi-conductor overhead transmission lines with validated results against textbook examples.

## Features

- **Data-Driven Architecture**: JSON-based configuration for tower geometries and conductor properties
- **Scalable Design**: Handles any number of conductors and circuits
- **Validated Implementation**: Results match textbook examples with high precision
- **Professional Engineering**: Proper separation of impedance and potential GMR values for bundled conductors

## Validated Examples

### Example 3.3 - Single Circuit Tower
- 3 phase conductors + 2 earth wires
- Results validated against "Modelling of multi-conductor overhead lines and cables"
- Sequence impedance and susceptance matrices match textbook values

### Example 3.4 - 400kV Double Circuit Tower
- 6 phase conductors + 1 earth wire
- Complex vertical configuration with bundled conductors
- **Exact match** on potential coefficient matrix (P₁₁ = 101.773 km/μF)
- **Excellent match** on phase impedance (Z₁₁ = 0.0465+0.4066j Ω/km vs textbook 0.0470+0.4140j)

## Quick Start

```python
from transmission_line_calculator import OverheadLine, load_line_from_json

# Load configuration from JSON
conductors, freq, rho_earth = load_line_from_json('example_3_4_tower.json')

# Create line object
line = OverheadLine(conductors, freq, rho_earth)

# Calculate matrices
Z_full = line.calculate_series_impedance_matrix()
P_full = line.calculate_potential_matrix()
Z_phase = line.reduce_matrix_by_elimination(Z_full, line.phase_indices, line.earth_indices)
```

## JSON Configuration Schema

```json
{
  "name": "Tower Configuration Name",
  "system_parameters": {
    "frequency": 50,
    "earth_resistivity": 20
  },
  "conductor_types": {
    "phase_4x400_acsr": {
      "gmr_impedance": 0.21275,
      "gmr_potential": 0.224267,
      "r_ac": 0.0171
    }
  },
  "circuits": [
    { "id": "C1", "name": "Circuit 1" }
  ],
  "tower_geometry": [
    {
      "conductor_id": "1 (C1, Top)",
      "x": -6.93,
      "y": 32.26,
      "type": "phase_4x400_acsr",
      "circuit_id": "C1",
      "phase": "A"
    }
  ]
}
```

## Technical Implementation

### Core Algorithms
- **Carson-Clem Equations**: For series impedance matrix calculation
- **Maxwell Potential Coefficients**: For capacitance matrix calculation
- **Kron Reduction**: For eliminating earth wire effects
- **Image Method**: For earth return path modeling

### Key Features
- Supports complex tower geometries with multiple circuits
- Proper handling of bundled conductors (separate GMR for impedance vs potential)
- Earth resistivity modeling with equivalent depth calculation
- Matrix reduction techniques for phase-only analysis

## Dependencies

```
numpy
scipy
json (built-in)
```

## Installation

```bash
pip install numpy scipy
python transmission_line_calculator.py
```

## File Structure

```
├── transmission_line_calculator.py  # Main calculation engine
├── example_3_3_tower.json          # Single circuit configuration
├── example_3_4_tower.json          # Double circuit configuration
├── L23_tower.json                  # Complex multi-circuit example
└── README.md                       # This file
```

## Validation Results

| Parameter | Calculated | Textbook | Error |
|-----------|------------|----------|-------|
| P₁₁ (Example 3.4) | 101.773 km/μF | 101.773 km/μF | **0.0%** |
| Z₁₁ Real (Example 3.4) | 0.0465 Ω/km | 0.0470 Ω/km | **1.1%** |
| Z₁₁ Imag (Example 3.4) | 0.4066 Ω/km | 0.4140 Ω/km | **1.8%** |

## Future Development

This tool serves as the foundation for:
- EMI analysis between overhead lines and pipelines
- Trajectory-based interference calculations
- Multi-conductor system optimization
- Power system protection studies

## References

- "Modelling of multi-conductor overhead lines and cables" - Validated examples
- Carson-Clem earth return formulations
- IEEE standards for transmission line modeling

## License

Professional engineering tool - See license terms.

## Authors

Developed for electromagnetic interference analysis applications.
