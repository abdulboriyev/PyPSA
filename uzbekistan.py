import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import seaborn as sns
import os

# Load all data
demand_data = pd.read_csv("uzbekistan/demand_data.csv", parse_dates=["timestamp"], index_col="timestamp")
power_plants = pd.read_csv("uzbekistan/power_plants.csv")
transmission_data = pd.read_csv("uzbekistan/transmission_data.csv")
fuel_costs = pd.read_csv("uzbekistan/fuel_costs.csv")
fuel_constraints = pd.read_csv("uzbekistan/fuel_constraints.csv").set_index("fuel")

# Remove duplicate rows in fuel_costs and power_plants
fuel_costs = fuel_costs.loc[~fuel_costs["fuel"].duplicated()]
power_plants = power_plants.drop_duplicates(subset=["name", "year"])

# Get all unique fuels
all_fuels = list(power_plants["fuel"].unique()) + ["import"]
all_fuels = pd.unique(all_fuels)  # Remove duplicates if any

# Main simulation function
def run_simulation(years):
    results = {}

    for year in years:
        print(f"\n{'=' * 40}\nProcessing {year}\n{'=' * 40}")
        # Filter data for current year
        demand_year = demand_data[demand_data.index.year == year]
        plants_year = power_plants[power_plants["year"] == year]
        fuel_costs_year = fuel_costs[fuel_costs["year"] == year].set_index("fuel")["cost"]
        fuel_costs_year = fuel_costs_year[~fuel_costs_year.index.duplicated()]  # Remove duplicates

        # Check demand and capacity
        total_capacity = plants_year.groupby("fuel")["capacity"].sum()
        total_demand = demand_year.sum().sum()
        print(f"Total Capacity by Fuel:\n{total_capacity}")
        print(f"Total Demand: {total_demand:.2f} MWh")

        # Create network
        network = pypsa.Network()
        network.set_snapshots(demand_year.index)

        # Add buses
        for bus in ["bus_1", "bus_2", "bus_3"]:
            network.add("Bus", bus, v_nom=380)

        # Add transmission lines with an explicit carrier
        for _, line in transmission_data.iterrows():
            network.add("Line", line["name"],
                        bus0=line["bus0"], bus1=line["bus1"],
                        x=line["reactance"], r=line["resistance"],
                        s_nom=line["capacity"],
                        carrier="ac")  # Explicit carrier for AC lines

        # Add generators with time-varying constraints
        for _, plant in plants_year.iterrows():
            fuel = plant["fuel"]
            cost = fuel_costs_year.get(fuel, plant["cost"])
            constraints = fuel_constraints.loc[fuel]

            # Create time-varying availability profiles
            hours = network.snapshots.hour
            mask = (hours >= constraints["hour_min"]) & (hours <= constraints["hour_max"])

            p_max_pu = pd.Series(0.0, index=network.snapshots, dtype=float)
            p_min_pu = pd.Series(0.0, index=network.snapshots, dtype=float)

            p_max_pu.loc[mask] = constraints["max_capacity_factor"]
            p_min_pu.loc[mask] = constraints["min_capacity_factor"]

            network.add("Generator",
                        name=plant["name"],
                        bus=plant["bus"],
                        p_nom=plant["capacity"],
                        marginal_cost=cost,
                        carrier=fuel,  # Explicit carrier assignment
                        p_max_pu=p_max_pu,
                        p_min_pu=p_min_pu)

        # Add loads
        for bus in ["bus_1", "bus_2", "bus_3"]:
            network.add("Load", f"{bus}_load",
                        bus=bus,
                        p_set=demand_year[bus])

        # Add import generator with high cost (backup supply)
        for bus in ["bus_1", "bus_2", "bus_3"]:
            network.add("Generator",
                        name=f"{bus}_import",
                        bus=bus,
                        p_nom=1e6,  # Large capacity (effectively unlimited)
                        marginal_cost=200,  # High cost to prioritize local generation
                        carrier="import")


        # Solve and store results
        try:
            network.optimize(solver_name='highs')  # glpk, highs
            if network.objective is not None:
                results[year] = {
                    "generation": network.generators_t.p.copy(),
                    "total_cost": network.objective / 1e6  # € million
                }
                print(f"Successfully optimized {year} with total cost: {results[year]['total_cost']:.2f} M€")

                # Debug: Print generation by fuel type
                gen_by_fuel = results[year]["generation"].T.groupby(plants_year.set_index("name")["fuel"]).sum().T
                print(f"Generation by Fuel for {year}:\n{gen_by_fuel}")

            else:
                results[year] = {"generation": pd.DataFrame(), "total_cost": np.nan}
                print(f"Optimization failed for {year}: No objective value")

        except Exception as e:
            print(f"Optimization error for {year}: {str(e)}")
            results[year] = {"generation": pd.DataFrame(), "total_cost": np.nan}
    return results

# Process results with improved fuel aggregation
def process_results(results):
    processed = {}

    # Get all fuels including import
    global all_fuels  # Use the modified list from top

    for year, data in results.items():
        if not data["generation"].empty:
            # Get fuel mapping for active generators
            active_generators = data["generation"].columns
            fuel_map = power_plants[power_plants["name"].isin(active_generators)]
            fuel_map = fuel_map.set_index("name")["fuel"].to_dict()

            # Add mappings for import generators not in power_plants
            for gen_name in active_generators:
                if gen_name not in fuel_map:
                    if "_import" in gen_name:
                        fuel_map[gen_name] = "import"

            # Aggregate by fuel type
            try:
                gen = data["generation"].rename(columns=fuel_map)
                gen = gen.groupby(level=0, axis=1).sum()

                # Ensure all fuel columns exist
                for fuel in all_fuels:
                    if fuel not in gen.columns:
                        gen[fuel] = 0.0

                # Add time features
                gen["hour"] = gen.index.hour
                gen["month"] = gen.index.month

                processed[year] = {
                    "hourly": gen[list(all_fuels) + ["hour", "month"]],
                    "total_cost": data["total_cost"]
                }

            except Exception as e:
                print(f"Error processing {year}: {str(e)}")
                processed[year] = {"hourly": pd.DataFrame(), "total_cost": np.nan}
        else:
            processed[year] = {"hourly": pd.DataFrame(), "total_cost": np.nan}

    return processed

# Visualization functions remain the same...
def plot_results(processed_data, save_folder="results"):
    os.makedirs(save_folder, exist_ok=True)  # Ensure results folder exists

    # Improved color palette for fuels
    colors = {
        "solar": "#FDB813",  # Bright yellow-orange
        "wind": "#67B7DC",  # Light blue
        "hydro": "#4B89DC",  # Deep blue
        "coal": "#3D3D3D",  # Dark gray
        "gas": "#E74C3C",  # Red-orange
        "import": "#9B59B6",  # Purple
    }

    plt.style.use("seaborn-v0_8-darkgrid")  # Better aesthetics

    # Plot yearly generation mix
    fig, ax = plt.subplots(figsize=(12, 6))
    yearly_totals = pd.DataFrame({
        year: data["hourly"][list(colors.keys())].sum()
        for year, data in processed_data.items()
    }).T.fillna(0)

    yearly_totals.plot(kind="area", ax=ax, color=colors, stacked=True, alpha=0.85)
    ax.set_title("Yearly Generation Mix", fontsize=14, weight='bold', pad=10)
    ax.set_ylabel("GWh", fontsize=12)
    ax.set_xlabel("Year", fontsize=12)
    ax.legend(loc="upper left", title="Fuel Type", fontsize=10, title_fontsize=12)
    plt.xticks(fontsize=10)
    plt.yticks(fontsize=10)

    # Save yearly mix plot
    yearly_save_path = os.path.join(save_folder, "yearly_generation_mix.png")
    plt.savefig(yearly_save_path, dpi=300, bbox_inches="tight")
    print(f"Saved: {yearly_save_path}")
    plt.show()

    # Plot hourly generation for each year
    for year, data in processed_data.items():
        fig, ax = plt.subplots(figsize=(12, 6))

        if data["hourly"].empty:
            ax.text(0.5, 0.5, "Infeasible", ha='center', va='center', transform=ax.transAxes,
                    fontsize=14, color='red', weight='bold')
            ax.set_title(f"{year} - Infeasible", color='red', fontsize=14, weight='bold')
        else:
            hourly_avg = data["hourly"].groupby("hour").mean().drop(columns="month")
            hourly_avg.plot(kind="area", ax=ax, color=colors, stacked=True, alpha=0.9)

            ax.set_title(f"Hourly Generation Pattern - {year}", fontsize=14, weight='bold', pad=10)
            ax.set_xlabel("Hour of Day", fontsize=12)
            ax.set_ylabel("Power Generation (MW)", fontsize=12)
            ax.set_xticks(np.arange(0, 24, 2))
            ax.set_xlim(0, 23)
            ax.legend(loc="upper right", title="Fuel Type", fontsize=10, title_fontsize=12)

        # Save each hourly plot
        hourly_save_path = os.path.join(save_folder, f"hourly_generation_{year}.png")
        plt.savefig(hourly_save_path, dpi=300, bbox_inches="tight")
        print(f"Saved: {hourly_save_path}")
        plt.show()


# Run the simulation for years 2025 to 2032
years = list(range(2025, 2033))
simulation_results = run_simulation(years)

# Process results
processed_data = process_results(simulation_results)

# Plot the results
plot_results(processed_data)

# Compare demand and supply for the years

# Print costs
print("\nSystem Costs by Year (€ million):")
costs = pd.Series({year: data["total_cost"] for year, data in processed_data.items()})
print(costs.to_markdown(floatfmt=".2f"))