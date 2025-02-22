# Energy System Simulation with PyPSA

![PyPSA Version](https://img.shields.io/badge/PyPSA-0.20.1-brightgreen)
![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue)

A powerful energy system simulation framework for modeling electricity generation, transmission, and demand.

## Features

- **Hourly resolution** simulations
- **Multi-year analysis** (2025-2032)
- Supports:
  - Conventional power plants (Coal, Gas)
  - Renewable energy (Solar, Wind, Hydro)
  - Transmission network modeling
- Automatic optimization
- Interactive visualizations

## Installation

1. **Clone Repository**
```bash
git clone https://github.com/abdulboriyev/PyPSA.git
cd PyPSA
```

2. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```
## Data Requirements

**Input Files**
```
PyPSA/
├── data/
│   ├── demand_data.csv
│   ├── power_plants.csv
│   ├── transmission_data.csv
│   ├── fuel_costs.csv
│   └── fuel_constraints.csv
```

**Example Data Formats**
1. `demand_data.csv`
```
timestamp,bus_1,bus_2,bus_3
2025-01-01 00:00:00,1500,1800,2100
2025-01-01 01:00:00,1450,1750,2050
...
```

2. `power_plants.csv`
```
name,bus,fuel,capacity,cost,year
Plant_A,bus_1,gas,2500,50,2025
Plant_B,bus_2,coal,1200,30,2025
...
```

3. `transmission_data.csv`
```
name,bus0,bus1,reactance,resistance,capacity
Line_1,bus_1,bus_2,0.0001,0.0001,1000
...
```

4. `fuel_costs.csv`
```
fuel,cost,year
gas,30,2025
coal,20,2025
solar,3,2025
wind,3,2025
hydro,10,2025
gas,30,2026
...
```

5. `fuel_constraints.csv`
```
fuel,hour_min,hour_max,max_capacity_factor,min_capacity_factor
solar,6,18,1.0,0.0
wind,0,23,0.9,0.0
hydro,0,23,0.9,0.0
coal,0,23,1.0,0.0
gas,0,23,1.0,0.0
```

## Usage
Run the simulation:

```bash
python main.py
```

**Example Output**

```
==========================================
 ANALYSIS RESULTS 
==========================================
Period: 2025-01-01 to 2025-12-31
Total Cost: €42.15 million
Peak Demand: 21,000 MWh
Total Generation: 125,400 MWh

Generation Mix:
solar     18.9% (35,200 MWh)
wind      32.1% (59,800 MWh)
coal      29.4% (54,700 MWh)
import    19.6% (36,500 MWh)
```

## Configuration

Modify simulation parameters in `config.yaml`:
```
simulation:
  years: [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032]
  buses: ["bus_1", "bus_2", "bus_3"]
  
visualization:
  colors:
    solar: "#FFD700"
    wind: "#4682B4"
    coal: "#696969"
    gas: "#FF6347"
    import: "#9370DB"
```

## Code Structure

```
project-root/
├── data/                # Input data files
├── results/             # Output results
├── main.py              # Main simulation script
├── config.yaml          # Configuration file
├── README.md            # This documentation
└── requirements.txt     # Dependency list
```
