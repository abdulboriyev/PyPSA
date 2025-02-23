import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yaml
import os
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)


def load_config(config_path: str) -> dict:
    """Load and validate configuration file"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Validate required sections
    required_sections = ['simulation', 'fuels', 'network', 'visualization', 'data_paths']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")

    # Validate fuel_order uniqueness
    fuel_order = config['visualization'].get('fuel_order', [])
    if len(fuel_order) != len(set(fuel_order)):
        duplicates = [f for f in fuel_order if fuel_order.count(f) > 1]
        raise ValueError(f"Duplicate fuels in fuel_order: {duplicates}")

    return config


def validate_data(year: int, demand: pd.DataFrame, plants: pd.DataFrame, config: dict) -> None:
    """Validate input data integrity with enhanced checks"""
    if demand.empty:
        raise ValueError(f"No demand data for year {year}")
    if plants.empty:
        raise ValueError(f"No power plants data for year {year}")

    # Check for missing fuel definitions
    missing_fuels = set(plants['fuel']) - set(config['fuels'].keys())
    if missing_fuels:
        raise ValueError(f"Missing fuel constraints for: {', '.join(missing_fuels)}")

    # Check for duplicate generators
    duplicates = plants[plants.duplicated('name')]
    if not duplicates.empty:
        raise ValueError(f"Duplicate generator names: {duplicates['name'].tolist()}")


def create_network(config: dict, demand: pd.DataFrame) -> pypsa.Network:
    """Initialize PyPSA network with consistent carrier naming"""
    network = pypsa.Network()
    network.set_snapshots(demand.index)

    # Add buses with normalized carrier names
    for bus in config['network']['buses']:
        network.add("Bus", bus,
                    v_nom=config['network']['base_voltage'],
                    carrier=config['network'].get('bus_carrier', 'AC').lower())
    return network


def add_transmission(network: pypsa.Network, transmission_data: pd.DataFrame, config: dict) -> None:
    """Add transmission lines with normalized carrier names"""
    line_carrier = config['network'].get('line_carrier', 'AC').lower()

    for _, line in transmission_data.iterrows():
        network.add("Line",
                    name=line["name"],
                    bus0=line["bus0"],
                    bus1=line["bus1"],
                    x=line["reactance"],
                    r=line["resistance"],
                    s_nom=line["capacity"],
                    carrier=line_carrier)


def add_generators(network: pypsa.Network, plants: pd.DataFrame, config: dict) -> Dict[str, str]:
    """Add generators with fuel consistency checks"""
    fuel_map = {}
    seen_names = set()

    for _, plant in plants.iterrows():
        if plant["name"] in seen_names:
            raise ValueError(f"Duplicate generator name: {plant['name']}")
        seen_names.add(plant["name"])

        fuel = plant["fuel"].lower()  # Normalize to lowercase
        if fuel not in config['fuels']:
            raise ValueError(f"Undeclared fuel type: {fuel}")

        constraints = config['fuels'][fuel]
        hours = network.snapshots.hour
        mask = (hours >= constraints["hour_min"]) & (hours <= constraints["hour_max"])

        # Create capacity factors
        p_max_pu = pd.Series(0.0, index=network.snapshots)
        p_max_pu.loc[mask] = constraints["max_capacity_factor"]

        p_min_pu = pd.Series(constraints["min_capacity_factor"], index=network.snapshots)

        network.add("Generator",
                    name=plant["name"],
                    bus=plant["bus"],
                    p_nom=plant["capacity"],
                    marginal_cost=plant["cost"],
                    carrier=fuel,
                    p_max_pu=p_max_pu,
                    p_min_pu=p_min_pu)
        fuel_map[plant["name"]] = fuel

    return fuel_map


def process_results(results: Dict[int, Dict[str, Any]], config: dict) -> Dict[int, Dict[str, Any]]:
    """Process results with fuel order validation"""
    processed = {}
    fuel_order = [f.lower() for f in config['visualization']['fuel_order']]  # Normalized order

    for year, data in results.items():
        if data["status"] != "optimal":
            processed[year] = data
            continue

        try:
            # Ensure consistent fuel mapping
            gen = data["generation"].rename(columns=data["fuel_map"])

            # Group by fuel type (case-insensitive)
            gen = gen.groupby(lambda x: x.lower(), axis=1).sum()

            # Add missing fuels and enforce order
            for fuel in fuel_order:
                if fuel not in gen.columns:
                    gen[fuel] = 0.0
            gen = gen[fuel_order]

            # Add time features
            gen["hour"] = gen.index.hour
            gen["month"] = gen.index.month

            processed[year] = {
                "hourly": gen,
                "total_cost": data["total_cost"],
                "status": "optimal",
                "peak_demand": data["peak_demand"],
                "capacity": data["capacity"]
            }

        except Exception as e:
            logging.error(f"Error processing {year}: {str(e)}")
            processed[year] = data.update({"status": "processing_failed"})

    return processed


def plot_results(results: dict, config: dict) -> None:
    """Generate visualizations with safe fuel ordering"""
    vis = config['visualization']
    fuel_order = [f.lower() for f in vis['fuel_order']]  # Normalized order
    os.makedirs(vis['output_dir'], exist_ok=True)

    # Configure plot style
    plt.style.use(vis.get('style', 'seaborn-v0_8-darkgrid'))
    plt.rcParams.update({'font.size': vis.get('font_size', 12)})

    # Yearly generation mix plot
    valid_years = [y for y, d in results.items() if d.get("status") == "optimal"]
    if valid_years:
        yearly_totals = pd.DataFrame({
            y: results[y]["hourly"][fuel_order].sum()
            for y in valid_years
        }).T.fillna(0)

        fig, ax = plt.subplots(figsize=vis['figure_size'])
        yearly_totals.plot(kind="area", ax=ax,
                           color=vis['colors'],
                           stacked=True, alpha=vis.get('alpha', 0.85))
        ax.set_title(vis.get('yearly_title', 'Yearly Generation Mix'))
        ax.set_ylabel(vis.get('yearly_ylabel', 'Generation (GWh)'))
        plt.savefig(os.path.join(vis['output_dir'], 'yearly_generation_mix.png'),
                    dpi=vis.get('dpi', 300), bbox_inches='tight')
        plt.close()

    # Hourly profiles with error handling
    for year, data in results.items():
        fig, ax = plt.subplots(figsize=vis['figure_size'])
        if data.get("status") != "optimal":
            error_text = "\n".join([
                f"Status: {data.get('status', 'unknown')}",
                f"Reason: {data.get('message', 'Unknown error')}",
                f"Peak Demand: {data.get('peak_demand', 'N/A'):.2f} MW",
                f"Capacity: {data.get('capacity', 'N/A'):.2f} MW"
            ])
            ax.text(0.5, 0.5, error_text, ha='center', va='center',
                    transform=ax.transAxes, fontsize=12, color='red')
            ax.set_title(f"{year} - Processing Failed")
        else:
            hourly = data["hourly"].groupby("hour").mean()[fuel_order]
            hourly.plot(kind='area', ax=ax, color=vis['colors'],
                        stacked=True, alpha=vis.get('alpha', 0.85))
            ax.set_title(f"{vis.get('hourly_title', 'Hourly Generation')} - {year}")
            ax.set_xlabel(vis.get('hourly_xlabel', 'Hour of Day'))
            ax.set_ylabel(vis.get('hourly_ylabel', 'Power (MW)'))

        plt.savefig(os.path.join(vis['output_dir'], f'hourly_generation_{year}.png'),
                    dpi=vis.get('dpi', 300), bbox_inches='tight')
        plt.close()


def add_loads(network: pypsa.Network, demand: pd.DataFrame, config: dict) -> None:
    """Add loads with validation"""
    for bus in config['network']['buses']:
        if bus not in demand.columns:
            raise ValueError(f"Missing demand data for bus {bus}")
        network.add("Load",
                    name=f"{bus}_load",
                    bus=bus,
                    p_set=demand[bus].astype(np.float64)
                    )
def add_import_generators(network: pypsa.Network, config: dict) -> Dict[str, str]:
    """Add import generators and extend fuel map"""
    fuel_map = {}
    for bus in config['network']['buses']:
        gen_name = f"{bus}_import"
        network.add("Generator",
                    name=gen_name,
                    bus=bus,
                    p_nom=1e6,
                    marginal_cost=200,
                    carrier="import"
                    )
        fuel_map[gen_name] = "import"
    return fuel_map

def check_system_adequacy(network: pypsa.Network, year: int) -> None:
    """Validate system capacity meets demand"""
    total_capacity = network.generators.p_nom.sum()
    peak_demand = network.loads_t.p_set.sum(axis=1).max()

    logging.info(f"System Adequacy Check for {year}:")
    logging.info(f"Total Capacity: {total_capacity:.2f} MW")
    logging.info(f"Peak Demand: {peak_demand:.2f} MW")

    if total_capacity < peak_demand:
        raise ValueError(f"Insufficient capacity in {year}: Deficit {peak_demand - total_capacity:.2f} MW")

def run_simulation(years: list, config: dict) -> Dict[int, Dict[str, Any]]:
    """Main simulation workflow with enhanced error handling"""
    results = {}

    # Load input data
    demand_data = pd.read_csv(config['data_paths']['demand'],
                              parse_dates=["timestamp"],
                              index_col="timestamp")
    plants = pd.read_csv(config['data_paths']['power_plants'])
    transmission_data = pd.read_csv(config['data_paths']['transmission'])

    for year in years:
        try:
            logging.info(f"\n{'=' * 40}\nProcessing {year}\n{'=' * 40}")

            # Filter yearly data
            demand_year = demand_data[demand_data.index.year == year]
            plants_year = plants[plants["year"] == year].copy()

            # Data validation
            validate_data(year, demand_year, plants_year, config)

            # Create network
            network = create_network(config, demand_year)
            add_transmission(network, transmission_data, config)
            fuel_map = add_generators(network, plants_year, config)
            add_loads(network, demand_year, config)
            fuel_map.update(add_import_generators(network, config))

            # Validate system adequacy
            check_system_adequacy(network, year)

            # Solve network
            network.optimize(solver_name='highs')

            # Store results
            if network.model.status == "ok":
                results[year] = {
                    "generation": network.generators_t.p.copy(),
                    "total_cost": network.model.objective.value / 1e6,
                    "status": "optimal",
                    "fuel_map": fuel_map,
                    "peak_demand": network.loads_t.p_set.sum(axis=1).max(),
                    "capacity": network.generators.p_nom.sum()
                }
            else:
                raise RuntimeError(f"Optimization failed: {network.model.status}")

        except Exception as e:
            logging.error(f"Error processing {year}: {str(e)}")
            results[year] = {
                "generation": pd.DataFrame(),
                "total_cost": np.nan,
                "status": "failed",
                "fuel_map": {},
                "message": str(e),
                "peak_demand": demand_year.sum().sum() if not demand_year.empty else np.nan,
                "capacity": plants_year["capacity"].sum() if not plants_year.empty else np.nan
            }

    return results


def format_results(processed_data: dict, config: dict) -> None:
    """Print formatted simulation results to console"""
    border = "=" * 42
    for year, data in processed_data.items():
        # Handle failed simulations
        if data.get("status") != "optimal":
            print(f"\n{border}\n Simulation Results: {year} - INFEASIBLE\n{border}")
            print(f"Reason: {data.get('message', 'Unknown error')}")
            print(f"Peak Demand: {data.get('peak_demand', 0):,.0f} {config['visualization']['units']['power']}")
            print(f"Available Capacity: {data.get('capacity', 0):,.0f} {config['visualization']['units']['power']}")
            continue

        # Calculate generation statistics
        hourly_data = data["hourly"].drop(columns=["hour", "month"], errors="ignore")
        total_gen = hourly_data.sum().sum()
        fuel_mix = hourly_data.sum()

        # Get ordered fuel list from config
        fuel_order = config['visualization']['fuel_order']
        ordered_fuels = [f for f in fuel_order if f in fuel_mix.index]

        print(f"\n{border}\n Simulation Results: {year}\n{border}")
        print(f"Total System Cost: €{data['total_cost']:.2f}M")
        print(f"Peak Demand: {data.get('peak_demand', 'N/A'):,.0f} {config['visualization']['units']['power']}")
        print(f"Total Generation: {total_gen:,.0f} {config['visualization']['units']['energy']}\n")

        print("Generation Mix:")
        for i, fuel in enumerate(ordered_fuels):
            prefix = "└──" if i == len(ordered_fuels) - 1 else "├──"
            percentage = (fuel_mix[fuel] / total_gen * 100).round(1)
            print(f"{prefix} {fuel.title():<6} {percentage:>5.1f}% "
                  f"({fuel_mix[fuel]:,.0f} {config['visualization']['units']['energy']})")


# In main execution
if __name__ == "__main__":
    config = load_config("config.yaml")
    raw_results = run_simulation(config['simulation']['years'], config)
    processed_results = process_results(raw_results, config)
    format_results(processed_results, config)  # Pass processed data
    plot_results(processed_results, config)