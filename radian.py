# -*- coding: utf-8 -*-
"""
Ported on Monday Sept 29 10:06am 2025
Starting conversion to a Flask web application
@author: paddy
"""
# Package imports
import random
from random import randint
import time

import os
import osmnx as ox
import json
import string
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import contextily as cx
import warnings
from tqdm import tqdm
import exrex

# voroni generation packages
from shapely.ops import unary_union#, cascaded_union

# k-means clustering packages
from sklearn.cluster import KMeans

# misc json and shapely packages
import shapely
from shapely.geometry import Point
from shapely.geometry import box
from geovoronoi import voronoi_regions_from_coords, points_to_coords
# This function takes in a Shapely Polygon object and returns a GeoDataFrame consisting of Voronoi-based buffers
# centred around either the true centroid of the original Polygon, or around a randomly generated "moving centroid"
# The function has three different forms of generation:
# 'eq' = Equal-area Voronoi generation centred around the original polygon centroid
# 'area' = Variable-area generation (Smaller Voronoi towards the centroid, larger towards the borders)
# 'rand' = Equal-area Voronoi generation centred around a random "moving centroid"

global glob_random_seed
glob_random_seed = randint(0, 99999999)

# Suppress depreciation warnings
warnings.filterwarnings('ignore')

def poly_bb_ratio(poly):
    min_x, min_y, max_x, max_y = poly.bounds
    bb = gpd.GeoSeries(box(min_x, min_y, max_x, max_y, ccw=True))
    ratio = float(1/(poly.area/bb.area))
    if ratio < 1.8:
        return 1.8
    return ratio

########## POINT GENERATION ##########

def points_uniform(poly, num_points, epsg=4326):
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
        points_found = False   
        min_x, min_y, max_x, max_y = geom.bounds
        poly_ratio = poly_bb_ratio(geom)
        points = []
        # Generates points repeatedly with a uniform generation within the bounds of the polygon
        while len(points) < round(num_points * 3):
            points.append(Point([random.uniform(min_x, max_x), random.uniform(min_y, max_y)]))
        gdf = gpd.GeoDataFrame(pd.DataFrame(points, columns=['geometry']), geometry='geometry', crs=epsg)
        gdf = gdf.sjoin(poly, predicate='within')
        gdf = gdf[['geometry']].iloc[0:num_points].reset_index(drop=True)
        points_out = pd.concat([points_out, gdf], ignore_index=True)
    return points_out
    
def points_moving_centre(poly, num_points, epsg=4326):
    """
    Return a GeoDataFrame containing a set of radially distributed, random points
    centred around a "rolling" centroid.

    Works for both single and multiple geometries present in the gdf.

    @type poly: geodataframe
    @param poly: GDF containing polygons
    @type num_points: integer
    @param num_points: Number of uniform points to be generated within each geometry
    """

    points_out = gpd.GeoDataFrame(geometry=[], crs=epsg)
    
    for geom in poly.geometry:
        min_x, min_y, max_x, max_y = geom.bounds
        geom_gdf = gpd.GeoDataFrame(geometry=[geom], crs=epsg)

        cx, cy = geom.centroid.x, geom.centroid.y
        max_pt = Point(max_x, max_y)
        radius = max_pt.distance(geom.centroid)

        # Moving centroid is generated in an eliptical region around the original centroid
        range_x = (max_x - min_x) / 4
        range_y = (max_y - min_y) / 16
        centroid_point = Point([random.uniform(cx - range_x, cx + range_x), random.uniform(cy - range_y, cy + range_y)])

        # Number of sections is set as well as the number of points assigned to each section
        section_num = 5
        section_size = (radius * 0.8) / section_num
        section_pts = round(num_points / section_num)

        # Values used to shift point locations to account for the moving centroid generation
        cent_diff_x = (cx - centroid_point.x) / section_num
        cent_diff_y = (cy - centroid_point.y) / section_num

        points_gdf = gpd.GeoDataFrame([])
        # Points are generated section by section
        for i in range(0, section_num):
            if num_points % 5 != 0:
                if i == 4:
                    temp = section_pts * i
                    section_pts = num_points - temp
            # Current circular buffer is created within which to generate points
            point_current = Point([centroid_point.x + (cent_diff_x * i), centroid_point.y + (cent_diff_y * i)])
            c_current = point_current.buffer(section_size * (i + 1))


            min_x, min_y, max_x, max_y = c_current.bounds
            buffer_gdf = gpd.GeoDataFrame(geometry=[c_current], crs=epsg)
            buffer_ratio = 3#poly_bb_ratio(c_current)

            # This while loop controls the generation of points in the current section
            current_list = []
            while len(current_list) < section_pts * buffer_ratio:
                # here we generate a point using a uniform distribution to set the possible x and y ranges
                current_list.append(Point([random.uniform(min_x, max_x), random.uniform(min_y, max_y)]))

            gdf = gpd.GeoDataFrame(pd.DataFrame(current_list, columns=['geometry']), geometry='geometry', crs=4326)
            gdf = gdf.sjoin(buffer_gdf, predicate='within')
            gdf = gdf.drop(['index_right'], axis=1)
            gdf = gdf.sjoin(geom_gdf, predicate='within')
            gdf = gdf.drop(['index_right'], axis=1)
            points_gdf = pd.concat([points_gdf, gdf],ignore_index=True)
        points_gdf = points_gdf[['geometry']].iloc[0:num_points].reset_index(drop=True)
        points_out = pd.concat([points_out, points_gdf], ignore_index=True)
    return points_out

def points_centre(poly, num_points, epsg=4326):
    """
    Return a GeoDataFrame containing a set of radially distributed, random points
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
        # When a multipolygon is generated and passed here an error is thrown - need to catch seed of it not working
        geom_gdf = gpd.GeoDataFrame(geometry=[geom], crs=epsg)

        cx, cy = geom.centroid.x, geom.centroid.y
        max_pt = Point(max_x, max_y)
        radius = max_pt.distance(geom.centroid)
        
        section_num = 5
        section_size = (radius * 0.8) / section_num
        section_pts = round(num_points / section_num)
        points_gdf = gpd.GeoDataFrame([])
        for i in range(0, section_num):
            if num_points % 5 != 0:
                if i == 4:
                    temp = section_pts * i
                    section_pts = num_points - temp
            c_current = geom.centroid.buffer(section_size * (i+1))
            min_x, min_y, max_x, max_y = c_current.bounds
            buffer_gdf = gpd.GeoDataFrame(pd.DataFrame([c_current], columns=['geometry']), geometry='geometry')
            current_list = []
            while len(current_list) < section_pts*3:
                current_list.append(Point([random.uniform(min_x, max_x), random.uniform(min_y, max_y)]))
                
            gdf = gpd.GeoDataFrame(pd.DataFrame(current_list, columns=['geometry']), geometry='geometry')
            gdf = gdf.sjoin(buffer_gdf, predicate='within')
            gdf = gdf.drop(['index_right'], axis=1)
            gdf = gdf.sjoin(geom_gdf, predicate='within')
            gdf = gdf.drop(['index_right'], axis=1)

            points_gdf = pd.concat([points_gdf, gdf], ignore_index=True)

        points_gdf = points_gdf.iloc[0:num_points].reset_index(drop=True)
        points_out = pd.concat([points_out, points_gdf], ignore_index=True)
    return points_out

def gaussian_centre(poly, num_points, epsg=4326):
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
    return points_out

def gaussian_moving_centre(poly, num_points, centre, epsg=4326):
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
        cx, cy = centre.x, centre.y
        sd_x = (max_y - min_y)/3
        sd_y = (max_x - min_x)/3
        cov = np.array([[sd_y**2, 0], [0, sd_x**2]])
        while not points_found:
            pts = pd.DataFrame(np.random.multivariate_normal((cx, cy), cov, size=int(round(num_points*4))), columns=['x','y'])
            geo_pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(pts['x'], pts['y'], crs=epsg))
            geo_pts = geo_pts.sjoin(gpd.GeoDataFrame(geometry=gpd.GeoSeries([geom]), crs=epsg), predicate='within')
            if num_points < len(geo_pts):
                geo_pts = geo_pts.sample(num_points)
                points_found = True
            else:
                print("issue found in Gaussian moving centre")
                print("generated points = ", len(geo_pts), ", sample size = ", num_points)
        points_out = pd.concat([points_out, geo_pts], ignore_index=True)
    return points_out

########## VORONOI POLYGON GENERATION ##########

def kmeans_centroids(poly, num_points, num_cluster, eq_area):
    # Points are generated randomly in the polygon
    if(eq_area == 0): # Uniform distribution
        source = points_uniform(poly, num_points)  
    else: # Centroid-focused distribution
        source = points_centre(poly, num_points)

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

def moving_centroid(poly, epsg):
    cx, cy = poly.centroid.x, poly.centroid.y
    min_x, min_y, max_x, max_y = poly.bounds

    range_x = (max_x - min_x) / 4
    range_y = (max_y - min_y) / 16

    centroid_gdf = gpd.GeoDataFrame(pd.DataFrame([Point([random.uniform(cx - range_x, cx + range_x), random.uniform(cy - range_y, cy + range_y)])], columns=['geometry']), geometry='geometry', crs=3857)

    return centroid_gdf

def voronoi_gen(poly, poly_centroid, vor_num=12, gen_type='eq', epsg=4326): #'eq', 'area', 'rand'
    # Voronoi centroids are generated based on the specified generation type
    if(gen_type == 'eq'): # Equal-area uniformly distributed Voronoi regions
        vor_centroids = kmeans_centroids(poly, 500, vor_num, 0)
    elif(gen_type == 'area'): # Variable area, centrally focused Voronoi regions
        vor_centroids = kmeans_centroids(poly, 500, vor_num, 1)
    elif(gen_type == 'rand'): # Equal-area uniformly distributed Voronoi regions (with moving centroid)
        # Calculate moving centroid in an eliptical region around the original centroid
        gdf_centroid = poly_centroid
        vor_centroids = kmeans_centroids(poly, 500, vor_num, 0)
    # Setting crs to meter based projection

    # Convert the boundary geometry into a union of the polygon
    #boundary_shape = cascaded_union(poly) Depreciated
    boundary_shape = unary_union(poly)
    coords = points_to_coords(vor_centroids.geometry)

    # Calculating the voronoi regions
    region_polys, region_pts = voronoi_regions_from_coords(coords, boundary_shape)


    df = pd.DataFrame(list(region_polys.items()), columns=['index','geometry'])
    gdf_poly = gpd.GeoDataFrame(df, geometry='geometry', crs=epsg)

    # Calculating distance of Voronoi polygons to the centroid (moving or original)
    gdf_poly['dist_to_centre'] = 0
    for i in range(vor_num):
        if(gen_type == 'rand'):
            current = gdf_poly['geometry'][i].centroid.distance(gdf_centroid.iloc[0].geometry)
        else:
            current = gdf_poly['geometry'][i].centroid.distance(
            shapely.geometry.Point(poly.centroid.x, poly.centroid.y))
        gdf_poly['dist_to_centre'][i] = current

    # Assign a class to each polygon based on the distance to centroid
    # This will produce five distinct regions centred around the given moving/original centroid


    max_dist, min_dist = max(gdf_poly['dist_to_centre']), min(gdf_poly['dist_to_centre'])
    dist_break = (max_dist - min_dist) / 5
    gdf_poly['class'] = " "
    gdf_poly = gdf_poly.sort_values(by='dist_to_centre')
    gdf_poly['class'] = pd.cut(gdf_poly['dist_to_centre'], [0, dist_break, dist_break*2, dist_break*3, dist_break*4, np.inf], labels=[1,2,3,4,5])

    # Circular buffer visualization
    buffers = []
    title = "Voronoi-based Buffer Generation:\n"
    for i in range(5):
        if gen_type != 'rand':
            centroid = shapely.geometry.Point(poly.centroid.x, poly.centroid.y)
            c_current = centroid.buffer(dist_break * (i + 1))
            buffers.append(c_current)
        else:
            centroid = gdf_centroid#[0]
            c_current = centroid.buffer(dist_break * (i + 1))
            buffers.append(c_current)

    circ_df = pd.DataFrame(buffers, columns=['geometry'])
    #circ_gdf = gpd.GeoDataFrame(circ_df, geometry='geometry')

    #vor_union = gdf_poly.dissolve(by='class', as_index=False)

    #return gdf_poly.reset_index(drop=True).drop('index', axis=1)
    return gdf_poly[['geometry']].reset_index(drop=True)

########## ADDITIONAL METADATA FUNCTIONS
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


def generate_vars(gdf, rand_var_dict, web=False):
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
            case _:
                return
    return gdf

########### PRIMARY & SECONDARY GENERATION ##########

def points_ratio(total_pts, ratio):
    bulk_points = round(total_pts * ratio)
    local_points = total_pts - bulk_points
    return bulk_points, local_points

def primary_generation(source, source_centroid, total_pts, rand_centroid, epsg):
    if(rand_centroid):
        vor_polygons = voronoi_gen(source, source_centroid, 256, 'rand')
    else:
        vor_polygons = voronoi_gen(source, source_centroid, 256, 'eq')

    vor_union = gpd.GeoDataFrame(vor_polygons.dissolve(by='class', as_index=False)).set_crs(3857)
    
    if(total_pts > 0):
        vor_all = []
        for i in range(len(vor_union['geometry'])):
            current = cascaded_union(list(vor_union['geometry'][0:i + 1]))
            vor_all.append(current)

        vor_all = gpd.GeoDataFrame(pd.DataFrame(vor_all, columns=['geometry']), geometry='geometry', crs=3857)

        
        vor_points = int(np.ceil(total_pts / 5))
        primary_pts = gpd.GeoDataFrame(pd.DataFrame([], columns=['geometry']), geometry='geometry', crs=3857)
        for i in range(len(vor_all)):
            if(rand_centroid):
                gdf = points_moving_centre(vor_all['geometry'][i], vor_points)
            else:
                gdf = points_centre(vor_all['geometry'][i], vor_points)

            primary_pts = pd.concat([primary_pts, gdf], ignore_index=True)
    else:
        primary_pts = []

    missing_pts = total_pts - len(primary_pts)
    while(missing_pts > 0):
        temp_points = points_uniform(source, missing_pts*2)
        primary_pts = pd.concat([temp_points, primary_pts], ignore_index=True)
        missing_pts = total_pts - len(primary_pts)

    return primary_pts.iloc[0:total_pts].to_crs(epsg), vor_union.to_crs(epsg)

def secondary_gen_equal(source, source_centroid, total_pts, vor_num, epsg):
    #print("Starting secondary generation with equal-area Voronoi...")
    if vor_num > 256:
        vor_num = 256
        print("Max vor_num is 256!")
    elif vor_num <= 0:
        vor_num = 1
        print("Min vor_num is 1!")

    local_vor_points = int(np.ceil(total_pts / vor_num))

    local_vor_polygons = voronoi_gen(source, source_centroid, vor_num, 'eq')

    local_gdf = gpd.GeoDataFrame(pd.DataFrame([], columns=['geometry']), geometry='geometry', crs=epsg)
    for i in range(0, vor_num):
        current = points_centre(local_vor_polygons['geometry'][i], local_vor_points)
        local_gdf = pd.concat([local_gdf, current], ignore_index=True)

    return local_gdf.reset_index(drop=True), local_vor_polygons

def secondary_gen_var_area(source, source_centroid, total_pts, vor_num, epsg):
    #print("Starting secondary generation with variable-area Voronoi and area-based points...")
    if vor_num > 128:
        vor_num = 128
        print("Max poly_area value is 128!")
    elif vor_num <= 0:
        vor_num = 1
        print("Min vor_num is 1!")

    local_vor_points = round(total_pts / vor_num)

    local_vor_polygons = voronoi_gen(source, source_centroid, vor_num, 'area')

    # calculating the area of each polygon to determine the proportion of points in each
    local_area_union = local_vor_polygons.dissolve()
    local_area = local_area_union.area

    local_gdf = gpd.GeoDataFrame(pd.DataFrame([], columns=['geometry']), geometry='geometry', crs=epsg)

    for i in range(0, vor_num):
        area_prop = local_vor_polygons['geometry'][i].area / local_area
        current_local_points = int(total_pts * area_prop)
        current = points_centre(local_vor_polygons['geometry'][i], current_local_points)
        local_gdf = pd.concat([local_gdf, current], ignore_index=True)
    return local_gdf.reset_index(drop=True), local_vor_polygons

def secondary_gen_var_equal(source, source_centroid, total_pts, vor_num, epsg):
    #print("Starting secondary generation with variable-area Voronoi and equal points...")
    if vor_num > 128:
        vor_num = 128
        print("Max poly_area value is 128!")
    elif vor_num <= 0:
        vor_num = 1
        print("Min vor_num is 1!")

    local_vor_points = round(total_pts / vor_num)

    local_vor_polygons = voronoi_gen(source, source_centroid, vor_num, 'area')

    # the polyogn crs is set as the main polygon crs
    local_gdf = gpd.GeoDataFrame(pd.DataFrame([], columns=['geometry']), geometry='geometry', crs=epsg)
    for i in range(0, vor_num):
        current = points_centre(local_vor_polygons['geometry'][i], local_vor_points)
        local_gdf = pd.concat([local_gdf, current], ignore_index=True)

    return local_gdf.reset_index(drop=True), local_vor_polygons

def secondary_generation(source, source_centroid, total_pts, gen_type, vor_num, epsg):
    #### Local level generation ###

    # gen_type:
        # 0 for no local-level generation
        # 1 for Equal-area Voronoi local generation
        # 2 for Variable-area Voronoi local generation with points determined by area
        # 3 for Variable-area Voronoi local generation with equal points in each Voronoi

    # Set no local generation as the default
    if gen_type > 3:
        gen_type = 0


    # Local generation with approximately equal-area Voronoi polygons
    if gen_type == 1:
        local_gdf, local_vor_polygons = secondary_gen_equal(source, source_centroid, total_pts, vor_num, 3857)
        
    # Local generation with variable area Voronoi polygons with number of points based on area
    elif gen_type == 2:
        local_gdf, local_vor_polygons = secondary_gen_var_area(source, source_centroid, total_pts, vor_num, 3857)

    # Local generation with variable area Voronoi polygons with equal number of points in each
    elif gen_type == 3:
        local_gdf, local_vor_polygons = secondary_gen_var_equal(source, source_centroid, total_pts, vor_num, 3857)
    else:
        local_gdf = gpd.GeoDataFrame([])

    missing_pts = total_pts - len(local_gdf)
    if missing_pts > 0:
        temp_points = points_uniform(source, missing_pts)
        local_gdf = pd.concat([temp_points, local_gdf], ignore_index=True)

    return local_gdf.iloc[0:total_pts].reset_index(drop=True).to_crs(epsg), local_vor_polygons.reset_index(drop=True).to_crs(epsg)

############ NEW FEATURES (FROM RADIAN WEB) ###############

def road_distribution(roads, total_pts=100, road_offset=5, weighted=False, epsg=3857):
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

def radian():
    print("RADIAN (\u03C0) - Synthetic Spatial Data Generator")

    star_width = 128
    print('*' * star_width)

    # Loading running parameters from 'parameters.json'
    start_time = time.time()
    params = json.load(open("parameters.json"))
    set_seed = params["set_seed"]
    directory = os.path.dirname(params["filepath"])
    filepath = params["filepath"]
    epsg = params['epsg']
    total_pts = params["total_pts"]
    gen_type = params["gen_type"]
    ratio = (params["ratio"] / 100)
    vor_num = params["vor_num"]
    table_name = params["table_name"]
    
    random_var = params["random_var"]
    random_var_dict = params["random_var_dict"]

    rand_centroid = params["rand_centroid"]
    to_sql = params["to_sql"]
    to_geojson = params["to_geojson"]
    vor_to_geojson = params["vor_to_geojson"]
    vor_to_sql = params["vor_to_sql"]
    plot = params["plot"]
    basemap = params["basemap"]
    preview = params["preview"]

    null = params["missing_vals"]

    extra_var = params["extra_var"]
    extra_var_dict = params["extra_var_dict"]
    

    # Setting generation seed
    global glob_random_seed
    if set_seed:
        glob_random_seed = params["seed"]
        random.seed(glob_random_seed)
    else:
        glob_random_seed = random.randint(0, 2147483647)
        random.seed(glob_random_seed)

    print("* Generation seed: " + str(glob_random_seed))

    ########### LOADING SOURCE POLYGON(s)

    # Reading in the GeoJSON file, projecting to EPSG:3857 and checking for points density
    print(f"* Reading {filepath}...")
    file_name = os.path.basename(filepath)
    _, file_extension = os.path.splitext(file_name)
    if file_extension != '.geojson':
        print("invalid polygon file - please use .geojson format")
        return

    source_gdf = gpd.read_file(filepath)

    source_gdf = source_gdf.to_crs(epsg=3857)
    source_area = source_gdf.to_crs(epsg=8858)
    dens = total_pts/source_area.area[0]
    if(dens > 1):
        print("Points density too low: {} points in an area of {}".format(total_pts, source.area))
        print("Minimum points density is 1 point / m^2.")
        return

    

    ########## POINTS GENERATION ##########

    source = source_gdf.loc[0, 'geometry']
    
    if(rand_centroid):
        source_centroid = moving_centroid(source,epsg)
    else:
        source_centroid = source.centroid

    primary_total, secondary_total = points_ratio(total_pts, ratio)

    print(f"* Generating {primary_total} primary points and {secondary_total} secondary points in {file_name}")

    print(f"* Primary generation using {'moving centroid' if rand_centroid else 'true centroid'}")
    primary_points, primary_vor_polygons = primary_generation(source, source_centroid, primary_total, rand_centroid, epsg)

    if gen_type == 0:
        print(f"* No secondary generation.")
    print(f"* Secondary generation with {'equal area voronoi regions' if gen_type == 1 else ('variable-area voronoi regions by area' if gen_type == 2 else 'variable-area voronoi with equal points')}")
    secondary_points, local_vor_polygons = secondary_generation(source, source_centroid, secondary_total, gen_type, vor_num, epsg)


    #print(f"* Actual generation: {len(primary_points)} primary points, {len(secondary_points)} secondary points")

    # Merging the bulk and local point dataframes for output to SQL or GeoJSON

    #gdf_out = gpd.GeoDataFrame(primary_points.append(secondary_points, ignore_index=True), crs=epsg)     
    gdf_out = gpd.GeoDataFrame(pd.concat([primary_points, secondary_points], ignore_index=True), crs=epsg)     


    print("* Points generated successfully!")
    print('*' * star_width)

    ########## ADDITIONAL METADATA GENERATION ##########

    if random_var or extra_var:
        print("Generating Metadata:")

    if random_var:
        gdf_out = generate_vars(gdf_out, random_var_dict)

    if(extra_var):
        #print("Generating metadata...")
        for variable in extra_var_dict:
            gdf_out[f'{variable["name"]}'] = csv_distribute(variable['source'], total_pts)


    # Adding in null values last
    if null > 0:
        gdf_out = distribute_nans(gdf_out, null)

    ########## EXPORTING OF DATA ##########

    # Set exported CRS
    gdf_out = gdf_out.to_crs(epsg)
    source_gdf = source_gdf.to_crs(epsg) 

       
    # Exporting  data to GeoJSON
    if(to_geojson):
        if not os.path.exists(f"{directory}/GeoJSON"):
            os.makedirs(f"{directory}/GeoJSON")
        gdf_out.insert(0, 'PKID', range(0, len(gdf_out)))
        gdf_out.to_file(f"{directory}/GeoJSON/{table_name}.geojson", driver='GeoJSON')
        print("* Successfully created GeoJSON file {}.geojson with {} points".format(table_name, total_pts))

    # Exporting data to SQL dump file
    if(to_sql):
        gdf_out.drop(['PKID'], axis=1) # Bit hacky here, but the geometry being renamed to thegeom caused issues - will come back to this?
        if not os.path.exists(f"{directory}/SQL"):
            os.makedirs(f"{directory}/SQL")
        #def gdf_to_sql(table_name, gdf, num_rows, random_var, rand_var_types, rand_var_names, extra_var, extra_var_types, extra_var_name, extra_var_dict, directory):
        #gdf_to_sql_old(table_name, gdf_out, total_pts, random_var, rand_var_types, rand_var_names, extra_var, extra_var_types, extra_var_name, extra_var_dict, directory)
        
        print("pre-sql gdf:", gdf_out.head())
        
        gdf_to_sql_new(gdf_out, table_name, directory)

        print("post-sql gdf:", gdf_out.head())
        print("* SQL dump file created: {} rows to {} with table name: {}.".format(total_pts, f'{directory}/SQL/{table_name}.sql', table_name))

    # Exporting voronoi polygons
    if(gen_type > 0 and vor_to_geojson):
        # To GeoJSON
        if not os.path.exists(f"{directory}/GeoJSON"):
            os.makedirs(f"{directory}/GeoJSON")
        # make copy of local vor polys to set class to correct type and then export that?
        local_vor_polygons['class'] = local_vor_polygons['class'].astype(int)
        local_vor_polygons.to_file(f"{directory}/GeoJSON/{table_name}_voronoi_polygons.geojson", driver='GeoJSON')
        print("* Successfully created GeoJSON file {}_voronoi_polygons.geojson".format(table_name))

    if(gen_type > 0 and vor_to_sql):
        if not os.path.exists(f"{directory}/SQL"):
            os.makedirs(f"{directory}/SQL")
        # To SQL
        gdf_poly_to_sql("voronoi_poly_test", local_vor_polygons, directory)
        print("* SQL dump file created: {} rows to {} with table name: voronoi_poly_test.".format(total_pts, f'{directory}/SQL/{table_name}.sql'))

    end_time = time.time()

    ########## PRINTING GENERATION DIAGNOSTICS ##########
    
    print('*' * star_width)

    print("Generation Information:")
    
    print("* Generation time taken = ", (end_time-start_time))

    ########### DATA PREVIEW ##########

    print('*' * star_width)

    if(preview):
        print(f"Data Preview: Total points: {len(gdf_out)}\n", gdf_out.head())

    ########## PLOTTING DATA ##########()

    if(plot):
        plot_output(source_gdf, source_gdf.centroid, primary_vor_polygons, local_vor_polygons, local_vor_polygons.centroid, primary_points, secondary_points, basemap, epsg)

    print('*' * star_width)

def gauss_points(poly, num_points, epsg=4326):
    points_out = gpd.GeoDataFrame([])
    for geom in poly.geometry:
        min_x, min_y, max_x, max_y = geom.bounds
        cx, cy = geom.centroid.x, geom.centroid.y
        sd_x = (max_y - min_y)/4
        sd_y = (max_x - min_x)/4
        cov = np.array([[sd_y**2, 0], [0, sd_x**2]])
        pts = pd.DataFrame(np.random.multivariate_normal((cx, cy), cov, size=num_points), columns=['x','y'])
        geo_pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(pts['x'], pts['y'], crs=epsg))
        geo_pts = geo_pts.sjoin(gpd.GeoDataFrame(geometry=gpd.GeoSeries([geom]), crs=epsg), predicate='within')
        points_out = pd.concat([points_out, geo_pts], ignore_index=True)
    return points_out

def gauss_test(num_points, centre, bounds):
    min_x, min_y, max_x, max_y = (bounds[0],bounds[1],bounds[2],bounds[3])
    cx, cy = centre.x, centre.y
    sd_x = (max_y - min_y)/4
    sd_y = (max_x - min_x)/4
    cov = np.array([[sd_y**2, 0], [0, sd_x**2]])
    pts = pd.DataFrame(np.random.multivariate_normal((cx, cy), cov, size=num_points), columns=['x','y'])
    geo_pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(pts['x'], pts['y'], crs=epsg))
    return geo_pts

def test():
    print("RADIAN webapp testing...")
    epsg = 4326
    ireland = gpd.read_file("static/ireland.geojson").to_crs(epsg)
    ire_voronoi = voronoi_gen(ireland, ireland.centroid, 32, 'eq')

    test_square = gpd.GeoSeries(shapely.Polygon([(-2,-2),(-2,2),(2,2),(2,-2)]))
    test_centre = Point([1.5,-1.5])
    test_points = 10000

    # generate radian points and calculate time
    radian_start_time = time.time()
    radian_pts = points_centre(test_square, test_points, 4326)
    radian_end_time = time.time()

    # generate gaussian points and calculate time
    gauss_start_time = time.time()
    gauss_pts = gaussian_moving_centre(test_square, test_points, test_centre, 4326)
    gauss_end_time = time.time()

    print("time taken")
    radian_time = radian_end_time-radian_start_time
    gauss_time = gauss_end_time-gauss_start_time

    print("radian=", radian_time)
    print("gauss=", gauss_time)

    if radian_time < gauss_time:
        print("radian faster by ", gauss_time-radian_time, " seconds")
    else:
        print("gauss faster by ", radian_time-gauss_time, " seconds")

    

    fig, axs = plt.subplots(1,2,figsize=(10,8))
    for ax in axs:
        test_square.plot(ax=ax, edgecolor='green',facecolor='none')#

    axs[0].set_title("gaussian")
    gauss_pts.plot(ax=axs[0], color='blue', markersize=1)
    gpd.GeoSeries(test_centre).plot(ax=axs[0], color='red', markersize=3)
    axs[1].set_title("radian")
    radian_pts.plot(ax=axs[1], color='blue', markersize=1)

    plt.show()

    """
    pts = gauss_points(ireland, 125)
    fig, ax = plt.subplots(1,1,figsize=(10,8))
    ireland.plot(ax=ax, facecolor='none', edgecolor='green')
    pts.plot(ax=ax, color='red')
    plt.show()
    print("seed=", glob_random_seed)
    """
    

if __name__ == "__main__":
    bbox = gpd.read_file('bbox.geojson')
    for x in range(100):
        road_distribution(bbox, 100)
