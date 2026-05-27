import json
import geopandas as gpd
import radian_web
import shapely
import numpy as np
import pandas as pd
import random

from radian_web import points_uniform, gaussian_moving_centre, gaussian_centre
from radian_web import get_roads_from_poly, road_distribution, generate_vars

from flask import Flask, request, render_template
from flask import send_from_directory

glob_random_seed = random.randint(0,2147483647)
random.seed(glob_random_seed)

print("random seed = ", glob_random_seed)

app = Flask(__name__)
@app.route('/', methods=['GET','POST'])
def root():
    return render_template('index.html')


@app.route('/test', methods=['GET', 'POST'])
def process():
    poly = json.loads(request.data)
    gdf = gpd.GeoDataFrame.from_features(poly['data']['features'])
    
    num_points = poly['params']['num_points']
    vor_number = poly['params']['vor_number']
    gen_type = poly['params']['gen_type']
    points_split = poly['params']['points_split']
    centroid = shapely.Point(poly['centroid']['geometry']['coordinates'])
    covar = poly['params']['covar']

    print("covariance matrix:\n", covar)
    #min_x, min_y, max_x, max_y = gdf.bounds
    #cx, cy = centroid.x, centroid.y
    #sd_x = (max_y - min_y)/3
    #sd_y = (max_x - min_x)/3

    points_gdf = gpd.GeoDataFrame(geometry=[])
    vor_points_gdf = gpd.GeoDataFrame(geometry=[])
    # secondary generation
    if vor_number > 0 and poly['voronoi'] != None:
        print("generating secondary points")
        voronoi = gpd.GeoDataFrame.from_features(poly['voronoi']['features'])
        print(voronoi)
        primary = int(np.ceil(num_points * (points_split/100)))
        secondary = num_points - primary
        vor_points = int(np.ceil(secondary / vor_number))
        vor_points_gdf = gaussian_centre(voronoi, vor_points)
        vor_points_gdf = vor_points_gdf.sample(secondary).reset_index(drop=True)
    else:
        primary = num_points

    print("generating primary points")
    # primary generation
    if gen_type == 1:
        points_gdf = gaussian_moving_centre(gdf, primary, centroid, 4326, covar)
    else:
        points_gdf = points_uniform(gdf, primary)

    # combine primary and secondary points
    
    if len(points_gdf) == 0:
        return {'points':points_gdf.to_json()}
    if vor_number > 0 and poly['voronoi'] != None:
        points_out = pd.concat([points_gdf, vor_points_gdf], ignore_index=True)
        #return points_out.sample(len(points_out)).reset_index(drop=True).to_json()
        points_out['dist'] = shapely.distance(centroid, points_out.geometry)
        points_out['dist']= 1 - (points_out['dist']-points_out['dist'].min())/(points_out['dist'].max()-points_out['dist'].min())
        return {
            'points' : points_out.drop(['index_right','dist'], axis=1).sample(len(points_out)).reset_index(drop=True).to_json(),
            'voronoi': voronoi.to_json()
        }
    else:
        points_gdf['dist'] = shapely.distance(centroid, points_gdf.geometry)
        # (df-df.min())/(df.max()-df.min())
        points_gdf['dist']= 1 - (points_gdf['dist']-points_gdf['dist'].min())/(points_gdf['dist'].max()-points_gdf['dist'].min())
        return {'points':points_gdf.drop(['dist'],axis=1).to_json()}


@app.route('/getroads', methods=['GET', 'POST'])
def get_roads():
    request_json = json.loads(request.data)
    bbox = gpd.GeoDataFrame.from_features(request_json['data']['features'], crs=3857)
    roads_gdf = get_roads_from_poly(bbox)
    return {
        'roads' : roads_gdf.to_crs(4326).to_json()
    }

@app.route('/roadpoints', methods=['GET', 'POST'])
def get_road_points():
    request_json = json.loads(request.data)
    roads = gpd.GeoDataFrame.from_features(request_json['data']['features'], crs=4326).to_crs(3857)
    road_points = road_distribution(roads, request_json['params']['num_points'], road_offset=request_json['params']['road_offset'], weighted=True)
    return {
        'points': road_points.to_crs(4326).to_json(),
    }

@app.route('/voronoi', methods=['GET', 'POST'])
def voronoi():
    poly = json.loads(request.data)
    gdf = gpd.GeoDataFrame.from_features(poly['data']['features'])    
    vor_number = poly['params']['vor_number']    
    centroid = shapely.Point(poly['centroid']['geometry']['coordinates'])

    # secondary generation
    if vor_number > 0:
        voronoi_gdf = radian_web.voronoi_gen(gdf, centroid, vor_number)
    print(voronoi_gdf)
    return voronoi_gdf.to_json()

@app.route('/metadata', methods=['GET', 'POST'])
def metadata():
    points = json.loads(request.data)
    gdf = gpd.GeoDataFrame.from_features(points['data']['features'])    
    metaDict = points['params']
    for i, x in enumerate(metaDict):
        if x['type'] == 'str' or x['type'] == 'int':
            metaDict[i]['params'] = [int(n) for n in x['params']]
    metadata_gdf = generate_vars(gdf, metaDict, True)
    print(metadata_gdf.head())
    return {'points': metadata_gdf.to_json() }

@app.route('/save', methods=['GET', 'POST'])
def save():
    data = json.loads(request.get_data())
    gdf = gpd.GeoDataFrame.from_features(data)
    print(gdf.head(n=5))
    gdf.to_file("static/gdf.geojson")
    return send_from_directory(directory="static", path="gdf.geojson", as_attachment=True)


if __name__ == '__main__':
    app.run(host="localhost", port=8080, debug=False)