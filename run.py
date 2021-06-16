import geopandas as gpd
from rasterstats import zonal_stats as zs
import rasterio as rio
import os
from rasterio import features
import numpy as np
from shapely.geometry import shape
import glob

# Define paths
data_path = os.getenv('DATA_PATH', '/data')
inputs_path = os.path.join(data_path, 'inputs')
outputs_path = os.path.join(data_path, 'outputs')
if not os.path.exists(outputs_path):
    os.mkdir(outputs_path)
mastermap = glob.glob(os.path.join(inputs_path, 'mastermap', '*.gpkg'))[0]
udm_buildings = os.path.join(inputs_path, 'buildings', 'urban_fabric.gpkg')
output_file = os.path.join(outputs_path, 'features.gpkg')

threshold = float(os.getenv('THRESHOLD'))

buffer = 5

with rio.open(os.path.join(inputs_path, 'run/max_depth.tif')) as max_depth,\
        rio.open(os.path.join(inputs_path, 'run/max_vd_product.tif')) as max_vd_product:
    # Read MasterMap data
    buildings = gpd.read_file(mastermap, bbox=max_depth.bounds)
    if os.path.exists(udm_buildings):
        udm_buildings = gpd.read_file(udm_buildings, bbox=max_depth.bounds)
        udm_buildings['toid'] = 'udm' + udm_buildings.index.astype(str)
        buildings = buildings.append(udm_buildings)

    # Read flood depths and vd_product
    depth = max_depth.read(1)
    vd_product = max_vd_product.read(1)


    # Extract maximum depth and vd_product for each building
    buildings['depth'] = [row['max'] for row in zs(buildings.buffer(buffer), depth, affine=max_depth.transform, stats=['max'],
                                                   all_touched=True, nodata=max_depth.nodata)]

    buildings['vd_product'] = [row['max'] for row in zs(buildings.buffer(buffer), vd_product, affine=max_vd_product.transform, stats=['max'],
                                                        all_touched=True, nodata=max_vd_product.nodata)]

    # Find flooded areas
    flooded_areas = gpd.GeoDataFrame(
        geometry=[shape(s[0]) for s in features.shapes(
            np.ones(depth.shape, dtype=rio.uint8), mask=depth >= threshold, transform=max_depth.transform)], crs=max_depth.crs)

    # Filter buildings
    buildings = buildings[buildings.depth >= threshold]

    # Count the number of buildings by featurecode and save to CSV
    buildings[['toid', 'depth',  'vd_product']].to_csv(os.path.join(outputs_path, 'buildings.csv'), index=False)
