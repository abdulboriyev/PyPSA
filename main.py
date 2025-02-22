import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from matplotlib.dates import DateFormatter, HourLocator, DayLocator, MonthLocator


# ----------------------------
# Data Loading and Preparation
# ----------------------------
def load_data():
    """Load and validate all required datasets"""
    try:
        # Load and preprocess demand data
        demand_data = pd.read_csv(
            "example/demand_data.csv",
            parse_dates=["timestamp"],
            index_col="timestamp",
            dtype={"bus_1": float, "bus_2": float, "bus_3": float}
        ).asfreq('h').ffill()

        # Ensure proper datetime index
        demand_data.index = pd.to_datetime(demand_data.index).tz_localize(None)

        # Load other datasets
        power_plants = pd.read_csv("example/power_plants.csv", dtype={"year": int})
        transmission_data = pd.read_csv("example/transmission_data.csv")
        fuel_constraints = pd.read_csv("example/fuel_constraints.csv").set_index("fuel")

        # Visualization colors
        colors = {
            "solar": "#FFD700", "wind": "#4682B4", "hydro": "#20B2AA",
            "coal": "#696969", "gas": "#FF6347", "import": "#9370DB"
        }

        return demand_data, power_plants, transmission_data, fuel_constraints, colors

    except Exception as e:
        print(f"Data loading failed: {str(e)}")
        raise


# ---------------------
# Simulation Core
# ---------------------
def run_simulation(start_date, end_date, data):
    """Execute simulation with 10-day maximum period"""
    demand_data, power_plants, transmission_data, fuel_constraints, colors = data

    try:
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        # Enforce 10-day maximum period
        if (end_dt - start_dt) > pd.Timedelta(days=10):
            raise ValueError("Maximum allowed period is 10 days")

        sim_year = start_dt.year

        full_index = pd.date_range(start_dt, end_dt, freq='h', inclusive='both')
        demand = demand_data.reindex(full_index, method='ffill')[["bus_1", "bus_2", "bus_3"]]

        network = pypsa.Network()
        network.set_snapshots(full_index)

        add_network_components(network, demand, power_plants, transmission_data,
                               fuel_constraints, sim_year)

        network.optimize()
        return network, demand

    except Exception as e:
        print(f"Simulation error: {str(e)}")
        return None, None

def add_network_components(network, demand, plants_df, lines_df, fuel_constraints, sim_year):
    """Configure all network components"""
    # Add buses
    for bus in ["bus_1", "bus_2", "bus_3"]:
        network.add("Bus", name=bus, v_nom=380)

    # Add transmission lines
    for _, line in lines_df.iterrows():
        network.add("Line",
                    name=line["name"],
                    bus0=line["bus0"],
                    bus1=line["bus1"],
                    x=line["reactance"],
                    r=line["resistance"],
                    s_nom=line["capacity"],
                    carrier="AC")

    # Add active generators for simulation year
    active_plants = plants_df[plants_df["year"] == sim_year]
    for _, plant in active_plants.iterrows():
        fuel = plant["fuel"]
        constraints = fuel_constraints.loc[fuel]

        # Create time availability profile
        hours = network.snapshots.hour
        mask = ((hours >= constraints.get("hour_min", 0)) &
                (hours <= constraints.get("hour_max", 23)))

        # Set capacity factors
        p_max_pu = pd.Series(constraints.get("max_capacity_factor", 1),
                             index=network.snapshots)
        p_min_pu = pd.Series(constraints.get("min_capacity_factor", 0),
                             index=network.snapshots)
        p_max_pu[~mask] = 0
        p_min_pu[~mask] = 0

        network.add("Generator",
                    name=f"{plant['name']}_{sim_year}",
                    bus=plant["bus"],
                    p_nom=plant["capacity"],
                    marginal_cost=plant["cost"],
                    carrier=fuel,
                    p_max_pu=p_max_pu,
                    p_min_pu=p_min_pu)

    # Add loads and backup imports
    for bus in ["bus_1", "bus_2", "bus_3"]:
        network.add("Load", name=f"{bus}_load", bus=bus, p_set=demand[bus])
        network.add("Generator", name=f"{bus}_import", bus=bus,
                    p_nom=1e6, marginal_cost=200, carrier="import")


# ----------------------
# Results Processing
# ----------------------
def process_results(network, demand):
    """Process results with 10-day limit handling"""
    if network is None:
        return None

    gen = network.generators_t.p.copy()
    gen.index = pd.to_datetime(gen.index)

    fuel_mapping = {col: "import" if "_import" in col
    else network.generators.carrier[col] for col in gen.columns}
    gen = gen.T.groupby(fuel_mapping).sum().T

    hourly_demand = demand.sum(axis=1)

    return {
        "gen": gen,
        "demand": hourly_demand,
        "start": gen.index[0],
        "end": gen.index[-1],
        "total_cost": network.objective / 1e6
    }


# ---------------------
# Visualization
# ---------------------
def visualize_results(results, colors):
    """Visualize with adaptive width and time formatting"""
    if not results:
        return

    # Calculate duration and set figure width
    duration_days = (results["end"] - results["start"]).days + 1
    fig_width = max(12, duration_days * 2)  # Minimum 12", 2" per day

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(fig_width, 8), gridspec_kw={'height_ratios': [1, 3]})

    # Generation Mix Pie Chart
    total_gen = results["gen"].sum()
    fuel_order = total_gen.sort_values(ascending=False).index
    colors_ordered = [colors.get(f, "#999999") for f in fuel_order]

    ax1.pie(total_gen[fuel_order],
            autopct=lambda p: f'{p:.1f}%\n({p * total_gen.sum() / 100:.0f} MWh)',
            colors=colors_ordered,
            wedgeprops={'linewidth': 0.5, 'edgecolor': 'white'})
    ax1.set_title(f"Generation Mix ({results['start'].date()} to {results['end'].date()})", pad=20)

    # Hourly Profile Plot
    results["gen"][fuel_order].plot.area(
        ax=ax2,
        color=colors_ordered,
        alpha=0.85,
        linewidth=0.5
    )
    results["demand"].plot(
        ax=ax2,
        style='k--',
        lw=1,
        label='System Demand'
    )

    # Time formatting based on duration
    if duration_days <= 3:
        locator = HourLocator(interval=6)
        formatter = DateFormatter('%H:%M\n%d-%b')
    else:
        locator = DayLocator()
        formatter = DateFormatter('%d-%b')

    ax2.xaxis.set_major_locator(locator)
    ax2.xaxis.set_major_formatter(formatter)
    ax2.set_xlim(results["start"], results["end"])
    ax2.set_ylabel('Hourly Energy [MWh]')
    ax2.legend(bbox_to_anchor=(1.15, 1), loc='upper left')
    ax2.grid(alpha=0.3)

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()


# ---------------------
# Main Interface
# ---------------------
def interactive_analysis():
    data = load_data()
    colors = data[-1]

    while True:
        print("\n" + "=" * 50)
        print(" Note: Maximum analysis period is 10 days")
        try:
            start = input("Enter start date (YYYY-MM-DD [HH:MM]): ").strip()
            end = input("Enter end date (YYYY-MM-DD [HH:MM]): ").strip()

            network, demand = run_simulation(start, end, data)
            results = process_results(network, demand) if network else None

            if results:
                print(f"\n{' ANALYSIS RESULTS ':=^50}")
                print(f" Period: {results['start'].date()} to {results['end'].date()}")
                print(f" Duration: {results['end'] - results['start']}")
                print(f" Total Cost: €{results['total_cost']:.2f} million")
                print(f" Peak Demand: {results['demand'].max():.0f} MWh")
                print(f" Total Generation: {results['gen'].sum().sum():.0f} MWh")
                visualize_results(results, colors)

        except Exception as e:
            print(f"\nError: {str(e)}")

        if input("\nPerform another analysis? (y/n): ").lower() != 'y':
            print("Exiting...")
            break


if __name__ == "__main__":
    interactive_analysis()