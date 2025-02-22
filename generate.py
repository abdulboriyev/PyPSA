import pandas as pd
import numpy as np


# ---------------------------
# 1. Generate Demand Data
# ---------------------------
def generate_demand_data(years):
    """Generate realistic hourly demand data with yearly variations."""
    demand_data = pd.DataFrame()

    # Yearly configuration parameters
    base_demand = {  # Base demand for first year (MWh)
        "bus_1": 1350,
        "bus_2": 1040,
        "bus_3": 1260
    }

    annual_growth_rate = 0.07  # 5% annual demand growth
    yearly_phase_shifts = np.random.uniform(-1, 1, size=len(years))  # Different daily peak times each year

    for i, year in enumerate(years):
        # Generate timestamps for this year
        timestamps = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31 23:00", freq="h")

        # Year-specific parameters
        growth_factor = (1 + annual_growth_rate) ** i  # Compounded growth
        year_phase = yearly_phase_shifts[i]  # Unique daily pattern shift

        # Hourly demand components
        hours = timestamps.hour
        day_of_week = timestamps.dayofweek  # 0=Monday to 6=Sunday

        # Year-specific daily pattern
        daily_pattern = (
          0.6 +
          0.4 * np.sin(2 * np.pi * (hours - 12 + year_phase) / 24)  # Shifted peak
        )

        # Weekend reduction with yearly variation
        weekend_reduction = 0.3 + np.random.uniform(-0.07, 0.07)  # 15-25% reduction
        weekly_pattern = 1.0 - weekend_reduction * (day_of_week >= 5)

        # Combine components with year-specific noise
        year_demand = pd.DataFrame()
        for bus in ["bus_1", "bus_2", "bus_3"]:
            # Generate unique noise pattern for each year-bus combination
            np.random.seed(year + ord(bus[0]))  # Seed based on year + bus letter
            noise = np.random.uniform(0.95, 1.05, len(timestamps))

            year_demand[bus] = (
              base_demand[bus] * growth_factor *
              daily_pattern * weekly_pattern * noise
            )

        # Add timestamps and concatenate
        year_demand["timestamp"] = timestamps
        demand_data = pd.concat([demand_data, year_demand])

    # demand_data.set_index("timestamp", inplace=True)
    return demand_data

# ---------------------------
# 2. Generate Power Plants Data
# ---------------------------
def generate_power_plants(years):
    """Generate power plant data with realistic attributes."""
    plant_data = {
        "name": ["Plant_A", "Plant_B", "Plant_C", "Plant_D", "Plant_E"],
        "bus": ["bus_1", "bus_2", "bus_3", "bus_1", "bus_2"],
        "fuel": ["gas", "coal", "solar", "wind", "hydro"],
        "capacity": [2500, 1200, 800, 600, 400],  # MW
        "cost": [50, 30, 2, 4, 10],  # $/MWh
        "build_year": [2020, 2023, 2028, 2022, 2007],
        "lifetime": [30, 40, 25, 25, 20]  # Years
    }

    # Expand for all years
    plants = []
    for year in years:
        for i in range(len(plant_data["name"])):
            if year >= plant_data["build_year"][i] and year < plant_data["build_year"][i] + plant_data["lifetime"][i]:
                plants.append({
                    "name": plant_data["name"][i],
                    "bus": plant_data["bus"][i],
                    "fuel": plant_data["fuel"][i],
                    "capacity": plant_data["capacity"][i],
                    "cost": plant_data["cost"][i],
                    "year": year
                })

    return pd.DataFrame(plants)


# ---------------------------
# 3. Generate Transmission Data
# ---------------------------
def generate_transmission_data():
    """Generate transmission line data."""
    return pd.DataFrame({
        "name": ["line_1", "line_2", "line_3", "line_4"],
        "bus0": ["bus_1", "bus_2", "bus_3", "bus_1"],
        "bus1": ["bus_2", "bus_3", "bus_1", "bus_3"],
        "capacity": [2000, 2500, 1800, 2000],  # MW
        "length": [150, 200, 120, 180],  # km
        "reactance": [0.1, 0.12, 0.08, 0.09],  # pu
        "resistance": [0.01, 0.012, 0.008, 0.009]  # pu
    })


# ---------------------------
# 4. Generate Fuel Costs
# ---------------------------
def generate_fuel_costs(years):
    """Generate fuel cost data."""
    fuels = ["gas", "coal", "solar", "wind", "hydro"]
    costs = [30, 20, 3, 3, 10]  # $/MWh

    fuel_costs = []
    for year in years:
        for fuel, cost in zip(fuels, costs):
            fuel_costs.append({
                "fuel": fuel,
                "cost": cost,
                "year": year
            })

    return pd.DataFrame(fuel_costs)


# ---------------------------
# 5. Generate Fuel Constraints
# ---------------------------
def generate_fuel_constraints():
    """Generate operational constraints for each fuel type."""
    return pd.DataFrame({
        "fuel": ["solar", "wind", "hydro", "coal", "gas"],
        "hour_min": [6, 0, 0, 0, 0],  # Solar only available 6-18
        "hour_max": [18, 23, 23, 23, 23],
        "max_capacity_factor": [1.0, 0.9, 0.9, 1.0, 1.0],  # Maximum output
        "min_capacity_factor": [0.0, 0.0, 0.0, 0.0, 0.0]  # Relaxed minimum output
    })


# ---------------------------
# 6. Main Function
# ---------------------------
def main():
    years = list(range(2025, 2033))

    # Generate all data
    demand_data = generate_demand_data(years)
    power_plants = generate_power_plants(years)
    transmission_data = generate_transmission_data()
    fuel_costs = generate_fuel_costs(years)
    fuel_constraints = generate_fuel_constraints()

    # Save to CSV
    demand_data.to_csv("example/demand_data.csv", index=False)
    power_plants.to_csv("example/power_plants.csv", index=False)
    transmission_data.to_csv("example/transmission_data.csv", index=False)
    fuel_costs.to_csv("example/fuel_costs.csv", index=False)
    fuel_constraints.to_csv("example/fuel_constraints.csv", index=False)

    print("✅ Example data generated successfully!")


if __name__ == "__main__":
    main()