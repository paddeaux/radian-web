# -*- coding: utf-8 -*-
"""
Ported on Monday Sept 29 10:06am 2025
Starting conversion to a Flask web application
@author: paddy
"""
##################### Package imports #####################
import random
import time
import osmnx as ox
import string
import geopandas as gpd
import pandas as pd
import numpy as np
import warnings
import exrex

from random import randint
from shapely.ops import unary_union
from sklearn.cluster import KMeans
from shapely.geometry import Point
from geovoronoi import voronoi_regions_from_coords, points_to_coords
from names_generator import generate_name

global glob_random_seed
glob_random_seed = randint(0, 99999999)

##################### Suppress depreciation warnings #####################
warnings.filterwarnings('ignore')

##################### Generation Functions #####################

def points_uniform(poly, num_points, epsg=4326, layer=0):
    """
    Return a GeoDataFrame containing a set of uniformly distributed, random points
    set within the bounds of the given geometry.

    Works for both single and multiple geometries present in the gdf.

    @type poly: geodataframe
    @param poly: GDF containing polygons
    @type num_points: integer
    @param num_points: Number of uniform points to be generated within each geometry
    """
    points_out = gpd.GeoDataFrame(geometry=[], crs=epsg)
    
    for geom in poly.geometry:
        min_x, min_y, max_x, max_y = geom.bounds
        points = []
        # Generates points repeatedly with a uniform generation within the bounds of the polygon
        while len(points) < round(num_points * 3):
            points.append(Point([random.uniform(min_x, max_x), random.uniform(min_y, max_y)]))
        gdf = gpd.GeoDataFrame(pd.DataFrame(points, columns=['geometry']), geometry='geometry', crs=epsg)
        gdf = gdf.sjoin(poly, predicate='within')
        gdf = gdf[['geometry']].iloc[0:num_points].reset_index(drop=True)
        points_out = pd.concat([points_out, gdf], ignore_index=True)
    points_out['layer'] = [layer for x in range(len(points_out.index))]
    return points_out


def gaussian_centre(poly, num_points, epsg=4326, layer=0):
    """
    Return a GeoDataFrame containing a set of Gaussian distributed, random points
    set within the bounds of the given geometry.

    Works for both single and multiple geometries present in the gdf.

    @type poly: geodataframe
    @param poly: GDF containing polygons
    @type num_points: integer
    @param num_points: Number of uniform points to be generated within each geometry
    """
    points_out = gpd.GeoDataFrame(geometry=[], crs=epsg)
    for geom in poly.geometry:
        points_found = False
        min_x, min_y, max_x, max_y = geom.bounds
        cx, cy = geom.centroid.x, geom.centroid.y
        sd_x = (max_y - min_y)/4
        sd_y = (max_x - min_x)/4
        cov = np.array([[sd_y**2, 0], [0, sd_x**2]])
        # running into occasional problem, where the spatial join removes too many points
        # simple workaround for now is to just repeat the process when this happens
        # such is the nature of random generation
        while not points_found:
            pts = pd.DataFrame(np.random.multivariate_normal((cx, cy), cov, size=int(round(num_points*4))), columns=['x','y'])
            geo_pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(pts['x'], pts['y'], crs=epsg))
            geo_pts = geo_pts.sjoin(gpd.GeoDataFrame(geometry=gpd.GeoSeries([geom]), crs=epsg), predicate='within')
            if num_points < len(geo_pts):
                geo_pts = geo_pts.sample(num_points)
                points_found = True
            else:
                print("issue found")
                print("generated points = ", len(geo_pts), ", sample size = ", num_points)
        points_out = pd.concat([points_out, geo_pts], ignore_index=True)
        points_out['layer'] = [layer for x in range(len(points_out.index))]
    return points_out

def gaussian_moving_centre(poly, num_points, centre, epsg=4326, covar=None, layer=0):
    """
    Return a GeoDataFrame containing a set of Gaussian distributed, random points
    set within the bounds of the given geometry.

    Works for both single and multiple geometries present in the gdf.

    @type poly: geodataframe
    @param poly: GDF containing polygons
    @type num_points: integer
    @param num_points: Number of uniform points to be generated within each geometry
    """
    poly = poly.set_crs(4326)
    poly = poly.to_crs(3857)
    centre = gpd.GeoSeries([centre], crs=4326).to_crs(3857)[0]
    points_out = gpd.GeoDataFrame(geometry=[], crs=3857)
    i_max = 1
    i = 0
    for geom in poly.geometry:
        points_found = False
        #min_x, min_y, max_x, max_y = geom.bounds
        cx, cy = centre.x, centre.y
        print("centre_x", cx, "centre_y", cy)
        print("covariance matrix:", covar)
        #sd_x = (max_y - min_y)/3
        #sd_y = (max_x - min_x)/3
        #cov = np.array([[sd_y**2, 0], [0, sd_x**2]])
        while not points_found:
            if i >= i_max:
                return gpd.GeoDataFrame(geometry=[], crs=3857)
            pts = pd.DataFrame(np.random.multivariate_normal((cx, cy), covar, size=int(round(num_points*4))), columns=['x','y'])
            geo_pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(pts['x'], pts['y'], crs=epsg))

            print(geo_pts)
            geo_pts = geo_pts.sjoin(gpd.GeoDataFrame(geometry=gpd.GeoSeries([geom]), crs=epsg), predicate='within')
            if num_points < len(geo_pts):
                geo_pts = geo_pts.sample(num_points)
                points_found = True
            else:
                print("issue found in Gaussian moving centre")
                print("generated points = ", len(geo_pts), ", sample size = ", num_points)
                i += 1
                
        points_out = pd.concat([points_out, geo_pts], ignore_index=True)
        points_out['layer'] = [layer for x in range(len(points_out.index))]

    return points_out.to_crs(4326)

def road_distribution(roads, total_pts=100, road_offset=5, weighted=False, epsg=3857, layer=0):
    points = []
    while len(points) < total_pts:
        try :
            random_road = roads.geometry.sample(1, weights=roads['length'] if weighted else None)
            random_offset = random_road.offset_curve(random.uniform(-road_offset, road_offset))
        except:
            print("offending road =", random_road, " type=", random_road.geom_type)
        
        sampled_point = random_offset.interpolate(random.uniform(-random_road.length, random_road.length), normalized=False).reset_index(drop=True)
        points.append(sampled_point.geometry[0])

    points_gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries(points), crs=epsg)
    points_gdf['layer'] = [layer for x in range(len(points_gdf.index))]
    return points_gdf

def get_roads_from_poly(bbox, epsg=3857):
    # query overpassturbo for all roads within the given bounding box region.
    tags = {'highway': True}
    print("starting osmnx query...")
    osmnx_start_ts = time.time()
    roads = ox.features_from_polygon(bbox.geometry[0], tags)
    roads = roads[(roads.geometry.type == "LineString") | (roads.geometry.type == "MultiLineString")]
    roads_clip = gpd.clip(roads, bbox)

    bbox = bbox.to_crs(epsg)
    roads_clip = roads_clip.to_crs(epsg)
    multi_roads = roads_clip[roads_clip.geometry.type == "MultiLineString"].geometry
    single_roads = roads_clip[roads_clip.geometry.type == "LineString"].geometry

    multi_to_single = [line for multiline in multi_roads.geometry for line in multiline.geoms]
    all_roads = gpd.GeoDataFrame(geometry=(list(single_roads.geometry) + multi_to_single), crs=epsg)
    all_roads['length'] = all_roads.geometry.length
    osmnx_end_ts = time.time()
    print("osmnx: time take = ", osmnx_end_ts - osmnx_start_ts)
    return all_roads

##################### Voronoi Generation #####################

def kmeans_centroids(poly, num_points, num_cluster):
    source = points_uniform(poly, num_points)  
    
    # The geometries of the Shapely points are converted to a numpy array for use in the kmeans algorithm
    feature_coords = np.array([[e.x, e.y] for e in source.geometry])

    # A kmeans object is created using the specified number of clusters
    kmeans = KMeans(num_cluster, random_state=glob_random_seed)
    kmeans.fit(feature_coords)

    # The cluster centres are stored as centroids, and this list is put into a GeoDataFrame and returned
    centroids = kmeans.cluster_centers_
    df = pd.DataFrame(centroids, columns=['x', 'y'])
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.x, df.y))

    return gdf


def voronoi_gen(poly, poly_centroid, vor_num=12, epsg=4326):
    # Voronoi centroids
    vor_centroids = kmeans_centroids(poly, 500, vor_num)

    # Convert the boundary geometry into a union of the polygon
    #boundary_shape = cascaded_union(poly) Depreciated
    boundary_shape = unary_union(poly)
    coords = points_to_coords(vor_centroids.geometry)

    # Calculating the voronoi regions
    region_polys, _ = voronoi_regions_from_coords(coords, boundary_shape)


    df = pd.DataFrame(list(region_polys.items()), columns=['index','geometry'])
    gdf_poly = gpd.GeoDataFrame(df, geometry='geometry', crs=epsg)
    return gdf_poly[['geometry']].reset_index(drop=True)

##################### METADATA FUNCTIONS #####################
def gdf_poly_to_sql(table_name, gdf, directory):
    # initializes an SQL output file
    
    sqlFile = open(f'{directory}/SQL/{table_name}_voronoi.sql','w')
    sqlFile.write("")
    sqlFile.close()

    sqlFile = open(f'{directory}/SQL/{table_name}_voronoi.sql', 'a')
    sqlFile.write('-- Voronoi polygon regions exported to SQL from the RADIAN Spatal Data Generator\n\n')
    
    sqlFile.write('DROP TABLE IF EXISTS {}; \n\n'.format(table_name))
    sqlFile.write('CREATE TABLE {} ( \n'.format(table_name))
    sqlFile.write('\tpkid SERIAL PRIMARY KEY NOT NULL, \n')
    sqlFile.write("\tthegeom GEOMETRY DEFAULT ST_GeomFromText('POINT(0,51)', 4326), \n")
    sqlFile.write("\tdist_to_centre NUMERIC,\n")
    sqlFile.write("\tpoly_class INTEGER\n")
    sqlFile.write('\n); \n\n')
    sqlFile.write('-- Spatial index is now created\n\n')
    # Creation of Spatial Index for the SQL file
    sqlFile.write('CREATE INDEX {}_spatial_index ON {} USING gist (thegeom); \n'.format(table_name, table_name))

    for row in gdf.itertuples():
        poly_coords = row[1].wkt
        query = f"INSERT into {table_name} (thegeom, "
        query += f"dist_to_centre, poly_class"
        query += f") VALUES (ST_SetSRID(ST_PolygonFromText('{poly_coords}'),3857), "
        query += f"{row[2]}, {row[3]}); \r"
        sqlFile.write(query)
    
    return

def gdf_to_sql_new(gdf, table_name, directory):

    ###### SQL BOILER PLATE ######
    
    # Opens up an SQL file based on the table name, writes to the file and closes it
    sqlFile = open(f'{directory}/SQL/{table_name}.sql', "w")
    sqlFile.write("")
    sqlFile.close()

    # Opens up the SQL file to append lines to it
    sqlFile = open(f'{directory}/SQL/{table_name}.sql', "a")

    # SQL statments to create the table as well as drop if exists the table are appended
    sqlFile.write('-- This is an automatically generated SQL table. This has been generated by the RADIAN tool (developer Mr. Paddy Gorry)\n\n')

    sqlFile.write('DROP TABLE IF EXISTS {}; \n\n'.format(table_name))

    sqlFile.write('CREATE TABLE {} ( \n'.format(table_name))
    sqlFile.write('\tpkid SERIAL PRIMARY KEY NOT NULL, \n')

    ###### BOILER PLATE ENDS ######

    def get_var_type(dtype):
        match dtype:
            case 'int64':
                return "INTEGER"
            case 'float64':
                return "REAL"
            case 'object':
                return "VARCHAR"
            case 'datetime64[ns]':
                return "TIMESTAMP"
            case 'geometry':
                return "GEOMETRY DEFAULT ST_GeomFromText('POINT(0,51)', 4326)"
            case _:
                return "NONE"    

    def ddl_column(col):
        return f"\t{col.name} {get_var_type(col.dtype)}"
        
    ###### DDL statements for creating variables from the gdf columns ######
    gdf.columns = ['thegeom' if x=='geometry' else x for x in gdf.columns]
    gdf_cols = [(gdf[gdf.columns[x]]) for x in range(0,len(gdf.columns))] # changed 1 to 0 in the range

    # 'geometry' is not a valid column name for the SQL file, so we check and change this
    geom_col_name = [col.name for col in gdf_cols if col.dtype=='geometry'][0]

    # PKID serial has already been created
    for i, col in enumerate(gdf_cols):
        sqlFile.write("{}{}".format(ddl_column(col), (",\n" if i < len(gdf.columns)-2 else "\n);"))) #-2 since we omit the first column (pkid)

    sqlFile.write('\n\n-- Spatial index is now created\n\n')

    # Creation of Spatial Index for the SQL file
    sqlFile.write(f"CREATE INDEX {table_name}_spatial_index ON {table_name} USING gist ({geom_col_name}); \n")

    test_row = gdf.iloc[[0]]

        
    def val_format(val):
        if pd.isnull(val):
            return "null"
        return f"'{val}'"

    ###### DDL Insert Statements ######
    def write_insert(row):
        sqlFile.write(f"INSERT INTO {table_name} (")
        [sqlFile.write(f"{col}, ") if i < len(row.columns)-1 else sqlFile.write(f"{col}) VALUES (") for i, col in enumerate(row.columns) if i > 0]
        #[sqlFile.write(f"{val_format(val)}, ") if i < len(row.values[0])-1 else sqlFile.write(f"{val_format(val)});\n") for i, val in enumerate(row.values[0]) if i > 0]
        [sqlFile.write(f"{val_format(val)}, ") if i < len(row.values[0])-1 else sqlFile.write(f"{val_format(val)});\n") for i, val in enumerate(row.values[0]) if i > 0]

    [write_insert(gdf.iloc[i:i+1, :]) for i in range(len(gdf))]

def csv_distribute(filename, num_values):
    source = pd.read_csv(filename, encoding='latin-1')
    if source.shape[1] < 2:
        return list(random.choices(source.iloc[:, 0], k = num_values))
    return list(random.choices(source.iloc[:, 0], weights = source.iloc[:, 1], k = num_values))

def distribute_nans(df, percent=[5,10]):
    if isinstance(percent, list): 
        print(df.size)
        nan_prop = [round(len(df) * (x/100)) for x in percent]
        for i, prop in enumerate(nan_prop):       
            change = df.iloc[:,i:i+1].sample(frac=1).index[0:prop]
            df.iloc[change, i:i+1] = None
            df.sort_index()
    else:
        nan_prop = round(len(df) * (percent/100))
        for i in range(df.shape[1]):       
            change = df.iloc[:,i:i+1].sample(frac=1).index[0:nan_prop]
            df.iloc[change, i:i+1] = None
            df.sort_index()
    
    return df

def generate_vars(gdf, rand_var_dict, place_name, web=False):
    for var in rand_var_dict:
        match var['type']:
            case 'int':
                gdf[f"{var['name']}"] = [randint(var['params'][0], var['params'][1]) for i in range(len(gdf.index))]
            case 'str':
                gdf[f"{var['name']}"] = [''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(var['params'][0])) for i in range(len(gdf.index))]
            case 'regex':
                gdf[f"{var['name']}"] = [exrex.getone(var['params'][0]) for i in range(len(gdf.index))]
            case 'ts':
                start = pd.to_datetime(var['params'][0])
                end = pd.to_datetime(var['params'][1])
                ts_start = start.value//10**9
                ts_end = end.value//10**9
                if web:
                    gdf[f"{var['name']}"] = list(np.random.randint(ts_start, ts_end, len(gdf.index)))
                else:
                    gdf[f"{var['name']}"] = list(pd.to_datetime(np.random.randint(ts_start, ts_end, len(gdf.index)), unit='s'))
            case 'osm':
                print("querying osm...")
                amenities = ox.features_from_place(place_name, {var['params'][0] : var['params'][1]}).reset_index(drop=True)['name'].dropna()
                print("done")
                names = amenities.sample(len(gdf.index), replace=True if len(amenities) < len(gdf.index) else False).reset_index(drop=True)
                print("how many we got? = ", sum(names.isnull()))
                print("names = ", names, "\ngdf = ", gdf.index)
                gdf[f"{var['name']}"] = names
                print("NaN values = ", sum(gdf[f"{var['name']}"].isna()))
            case 'name':
                gdf[f"{var['name']}"] = [generate_name(style='capital') for x in range(len(gdf.index))]
            case _:
                return
    return gdf


if __name__ == "__main__":
    print("Run server.py to launch the web-application.")