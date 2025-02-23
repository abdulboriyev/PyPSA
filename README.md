# Energy System Simulation Framework with PyPSA

![PyPSA Version](https://img.shields.io/badge/PyPSA-0.33.0-brightgreen)
![Python Version](https://img.shields.io/badge/Python-3.13%2B-blue)

A comprehensive framework for simulating electricity generation, transmission networks, and demand patterns using PyPSA (Python for Power System Analysis).

## Features

- **Multi-period simulations** (2025-2032)
- **High-resolution modeling** (hourly time steps)
- **Diverse generation portfolio:**
  - Conventional (Coal, Gas)
  - Renewable (Solar, Wind, Hydro)
  - Emergency import capacity
- **Advanced network modeling:**
  - AC power flow calculations
  - Transmission line constraints
- **Optimization capabilities:**
  - Cost-minimized dispatch
  - Capacity adequacy checks
- **Automated visualization:**
  - Hourly generation profiles
  - Annual energy mix breakdowns

## Installation

### Prerequisites
- Python 3.13+
- Highs solver (included with PyPSA)

### Setup
1. **Clone repository:**
```bash
git clone https://github.com/abdulboriyev/PyPSA.git
cd PyPSA
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

## Code Structure

```
PyPSA/
├── data/                # Input data files
├── results/             # Output results
├── main.py              # Main simulation script
├── config.yaml          # Configuration file
├── README.md            # This documentation
└── requirements.txt     # Dependency list
```


## Data Requirements

**Input Structure**
```
data/
├── demand_data.csv      # Load profiles
├── power_plants.csv     # Generation assets
├── transmission_data.csv # Grid configuration
```

**File Specifications**
1. Demand Data (`demand_data.csv`)
```
timestamp,bus_1,bus_2,bus_3
2025-01-01 00:00:00,1500,1800,2100
2025-01-01 01:00:00,1450,1750,2050
...
```

2. Power Plants (`power_plants.csv`)
```
name,bus,fuel,capacity,cost,year
Plant_A,bus_1,gas,2500,50,2027
Plant_B,bus_2,coal,1200,30,2035
Plant_D,bus_1,wind,600,4,2042
...
```

3. Transmission Network (`transmission_data.csv`)
```
name,bus0,bus1,capacity,length,reactance,resistance
line_1,bus_1,bus_2,2000,150,0.1,0.01
line_2,bus_2,bus_3,2500,200,0.12,0.012
...
```

## Usage
Run the simulation:

```bash
python main.py
```

### Example Output

```
==========================================
 Simulation Results: 2030
==========================================
Total System Cost: €789.53M
Peak Demand: 5,362 MW
Total Generation: 24,933,519 GWh

Generation Mix:
├── Coal    31.6% (7,878,522 GWh)
├── Gas     33.5% (8,349,870 GWh)
├── Solar   15.2% (3,790,744 GWh)
├── Wind    17.5% (4,361,119 GWh)
├── Hydro    0.0% (0 GWh)
└── Import   2.2% (553,264 GWh)
```
### Results
Sample outputs are saved in `results/` directory:
- Yearly Generation Mix
- Hourly Dispatch Pattern

### Images
![Image 1](https://github.com/abdulboriyev/PyPSA/blob/main/results/hourly_generation_2030.png?raw=true)
![Image 2](https://github.com/abdulboriyev/PyPSA/blob/main/results/yearly_generation_mix.png?raw=true)


## Configuration

Modify `config.yaml` for different scenarios:
```
# SIMULATION PARAMETERS
simulation:
  # List of years to simulate (2025-2032)
  years: [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032]

# NETWORK CONFIGURATION
network:
  # Available buses/nodes in the power system
  buses: ["bus_1", "bus_2", "bus_3"]
  # Base voltage level for the network (kV)
  base_voltage: 500
  # Electrical current type (AC/DC)
  bus_carrier: "AC"
  # Transmission line type
  line_carrier: "AC"

# FUEL OPERATIONAL CONSTRAINTS
fuels:
  solar:
    hour_min: 6       # Earliest operational hour (6am)
    hour_max: 18      # Latest operational hour (6pm)
    max_capacity_factor: 1.0  # Maximum output (100%)
    min_capacity_factor: 0.0  # Minimum output (0%)
  wind:
    hour_min: 0       # Operates 24 hours
    hour_max: 23
    max_capacity_factor: 0.9  # 90% max capacity
  coal:
    hour_min: 0       # Baseload plant (24/7 operation)
    hour_max: 23
    max_capacity_factor: 1.0  # Full output capability
  gas:
    hour_min: 0       # Flexible generation
    hour_max: 23
  hydro:
    hour_min: 0       # Dispatchable renewable
    hour_max: 23
    max_capacity_factor: 0.9  # 90% max capacity
    min_capacity_factor: 0    # Can be turned off

# VISUALIZATION SETTINGS
visualization:
  # Output configuration
  output_dir: "results"  # Save location for graphs
  format: "png"         # Image file format
  dpi: 300             # Image resolution
  
  # Chart styling
  figure_size: [12, 6] # Width/height in inches
  alpha: 0.85          # Transparency level
  xlim: [0, 23]        # X-axis limits (24h clock)
  xtick_interval: 2    # Hour labels every 2 hours
  show_legend: true    # Display chart legend
  
  # Fuel display order (determines stacking order in charts)
  fuel_order: [coal, gas, solar, wind, hydro, import]
  
  # Color palette for fuel types
  colors:
    solar: "#FFD700"  # Gold
    wind: "#4682B4"   # Steel Blue
    coal: "#3D3D3D"   # Dark Gray
    hydro: "#4B89DC"  # Dodger Blue
    gas: "#FF6347"    # Tomato Red
    import: "#9370DB" # Medium Purple
  
  # Font sizes
  font_sizes:
    title: 14    # Chart titles
    label: 12     # Axis labels
    legend: 10    # Legend text
    error: 12     # Error message text
  
  # Axis labels
  labels:
    hourly_x: "Hour of Day"
    hourly_y: "Power Generation (MW)"
  
  # Chart titles
  titles:
    yearly: "Annual Generation Mix"
    hourly: "Hourly Generation Profile"
    infeasible: "No Solution Found"

# DATA PATHS
data_paths:
  demand: "data/demand_data.csv"           # Load profiles
  power_plants: "data/power_plants.csv"    # Generator assets
  transmission: "data/transmission_data.csv" # Grid infrastructure
```

## Contact
- **Name:** Xojiakbar Abdulboriyev
- **Email:** x.abdulboriyev@newuu.uz
- Project Link: https://github.com/abdulboriyev/PyPSA.git

