$(document).ready(function(){
    var marker;
    var disableMarker = false;
    var map = L.map('map', {zoomControl: false}).fitWorld();
    
   
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 
        '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    // a layer group, used here like a container for markers
    var markersGroup = L.featureGroup();
    var polyGroup = L.featureGroup();
    var vorGroup = L.featureGroup();
    var pointGroup = L.featureGroup();
    var drawnGroup = L.featureGroup();
    var lineGroup = L.featureGroup();

    // gaussian covariance
    var polyVar_x;
    var polyVar_y;
    var polyCoVar;
    var polyCovarXY = 0;

    var polyArea = 0;
    var areaLimit = 10 // area limit for Roads distirbution in Km^2

    var metaDict = [];
    /*
    polyGroup.on('layeradd', function (e) {
        if (e.layerType == 'rectangle') {
            polyGroup.clearLayers();
            poly = e.layer
            polyGroup.addLayer(poly);
            console.log("drawn poly:", poly);
            drawnPolyArea = L.GeometryUtil.geodesicArea(poly.getLatLngs()[0]);
            console.log("polygon area is= ", (drawnPolyArea / 1000000).toFixed(2), "km^2");
        } else {
            polyArea = L.GeometryUtil.geodesicArea(e.layer.getLayers()[0].getLatLngs()[0]);
        }
    })
    */
    map.addLayer(markersGroup);
    map.addLayer(polyGroup);
    map.addLayer(vorGroup);
    map.addLayer(drawnGroup);
    map.addLayer(lineGroup);
    map.addLayer(pointGroup);
    
    var drawControl = new L.Control.Draw({
        draw: {
            polyline: false,
            polygon: false,
            circle: false,
            marker: false
        }
        
    });

    // getting issue sometimes where the map drags rather than let drawing occur properly lol doesn't make a difference
    map.on("draw:drawstart", function (e) {
        disableMarker = true;        
    })

    map.on("draw:drawstop", function (e) {
        disableMarker = false;        
    })

    map.on("draw:created", function (e) {
        if (e.layerType == 'rectangle') {
            polyGroup.clearLayers();
            poly = e.layer
            polyGroup.addLayer(poly);
            console.log("drawn poly:", poly);
            polyArea = L.GeometryUtil.geodesicArea(poly.getLatLngs()[0]);
            console.log("polygon area is= ", (polyArea / 1000000).toFixed(2), "km^2");
            refreshInfo()
        }
        if (e.layerType == 'marker') {
            markersGroup.clearLayers();
            markersGroup.addLayer(e.layer);
        }
        
    });

    map.on("click", function (e) {
        if (!disableMarker) {
            if (markersGroup.getLayers().length < 0) {
                markersGroup.addLayer(new L.marker(e.latlng));
            }
            else {
                markersGroup.clearLayers();
                markersGroup.addLayer(new L.marker(e.latlng));
            }
        }
    });


    var geojsonMarkerOptions = {
        radius: 4,
        fillColor: "#ff7800",
        color: "#000",
        weight: 1,
        opacity: 1,
        fillOpacity: 0.8
    };

    
    function getParams() {
        var gen_type;
        var bound_type;
        if (document.getElementById("gen_gaussian").checked){
            gen_type = 1;
        } else if (document.getElementById("gen_roads").checked){
            gen_type = 2;
        } else {
            gen_type = 0
        }

        return {
            "num_points" : +document.getElementById("random_points").value,
            "gen_type" : +gen_type,
            "vor_number" : +document.getElementById("vor_number").value,
            "points_split": +document.getElementById("points_split").value,
            "road_offset": 5, // need to set UI slider for this
            "covar" : polyCoVar
        }
    }
 
    // Function to stop mag dragging when mouse is near a control input
    function disableDragging(controlObj) {
        controlObj.getContainer().addEventListener('mouseover', function () {
            map.dragging.disable();
            map.doubleClickZoom.disable(); 
            disableMarker = true;
        });

        // Re-enable dragging when user's cursor leaves the element
        controlObj.getContainer().addEventListener('mouseout', function () {
            map.dragging.enable();
            map.doubleClickZoom.enable(); 
            disableMarker = false;
        });
    }

    // Custom button panels

    // UI Revamp
    // **************** Top Left **********************

    const searchBar = L.control({ position: 'topleft' });
    searchBar.onAdd = () => {
        const barDiv = L.DomUtil.create('div', 'searchbar-wrapper');
    barDiv.innerHTML = `
        <span class="tooltiptext tooltip-search">Specify a location within which to generate data</span>
        <input class="location-search" type="text" value="Dublin, Ireland" id="location" required>
        `;
        return barDiv;
    };

    // Loading boundary button
    const searchButton = L.control({ position: 'topleft' });
    searchButton.onAdd = () => {
        const buttonDiv = L.DomUtil.create('div', 'searchbutton-wrapper');
        buttonDiv.innerHTML = `
            <div class="tooltip">
                <span class="tooltiptext tooltip-load">Load boundary</span>
                <button class='button btn-icon search-btn' title='Find boundary' id='btn-map-load'><i class='fa-solid fa-magnifying-glass'></i></button>
            </div>
            `;
        buttonDiv.addEventListener('click', () => {
            console.log('load boundary')
            document.getElementById("btn-map-load").disabled = true;
            var geojsonFeature;
            var search_term = document.getElementById("location").value;
            if (search_term == "") {
                alert("Location required!")
                return
            }
            console.log(search_term)
            var polyCount = polyGroup.getLayers().length;
            console.log("number of polygons:", polyCount);
  
            url = 'https://nominatim.openstreetmap.org/search?q='+search_term+'&polygon_geojson=1&format=jsonv2';
            fetch(url).then(function(response) {
                return response.json();
            }).then(function(json) {
                geojsonFeature = json[0].geojson;
                if (polyCount < 1) {
                    L.geoJSON(geojsonFeature).addTo(polyGroup);
                }
                else {
                    polyGroup.clearLayers();
                    L.geoJSON(geojsonFeature).addTo(polyGroup);
                }
                polyBounds = L.latLngBounds(polyGroup.getLayers()[0].getLayers()[0].getLatLngs()[0]);
                polyArea = L.GeometryUtil.geodesicArea(polyGroup.getLayers()[0].getLayers()[0].getLatLngs()[0]);
                console.log("polyBounds:\nXmin = ", polyBounds._southWest.lng, " Xmax = ", polyBounds._northEast.lng);
                console.log("polyBounds:\nYmin = ", polyBounds._southWest.lat, " Ymax = ", polyBounds._northEast.lat);
                polyVar_x = (polyBounds._northEast.lat - polyBounds._southWest.lat)/3;
                polyVar_y = (polyBounds._northEast.lng - polyBounds._southWest.lng)/3;
                map.fitBounds(polyGroup.getBounds());
                refreshInfo();
                setCov();
            })
            document.getElementById('btn-generate').disabled = false;
            document.getElementById('btn-zoom').disabled = false;
            document.getElementById("btn-map-load").disabled = false;
        });
        return buttonDiv;
    };

    // Zoom to boundary button
    const zoomBoundary = L.control({ position: 'topleft' });
    zoomBoundary.onAdd = () => {
        const zoomDiv = L.DomUtil.create('div', 'zoom-wrapper');
        zoomDiv.innerHTML = `
            <div class="tooltip">
                <span class="tooltiptext tooltip-home">Zoom to boundary</span>
                <button class='button btn-icon' id='btn-zoom' title='Zoom to boundary' disabled><i class='fa-solid fa-house'></i></button>
            </div>
                `;
        zoomDiv.addEventListener('click', () => {
            console.log("zooming to data")
            map.fitBounds(polyGroup.getBounds());
        });
        return zoomDiv;
    };
    
    searchBar.addTo(map);
    disableDragging(searchBar);
    searchButton.addTo(map)
    disableDragging(searchButton);
    zoomBoundary.addTo(map);
    disableDragging(zoomBoundary);
    map.addControl(drawControl);

    L.control.zoom({
        position: 'topleft'
    }).addTo(map);
    
    
    // ***************************  bottomleft  ************************************
    
    const ratioSlider = L.control({ position: 'bottomleft'});
    ratioSlider.onAdd = () => {
        const ratioDiv = L.DomUtil.create('div', 'ratio-wrapper');
        ratioDiv.innerHTML = `
                <legend class="slide-legend">Points Ratio</legend>
                <div class='slidecontainer'>
                    <input type="range" class='slider inputs' value="50" id="points_split" name="points_split" min="0" max="100" step="1" oninput="this.nextElementSibling.value = this.value"/>
                    <output class='param-text'>50</output>%
                </div>`;
        return ratioDiv;
    }

    const pointSlider = L.control({ position: 'bottomleft'});
    pointSlider.onAdd = () => {
        const pointDiv = L.DomUtil.create('div', 'point-wrapper');
        pointDiv.innerHTML = `
            <legend class="slide-legend">Number of Points</legend>
                <div class='slidecontainer slide-tall'>
                    <input type="range" class='slider inputs' value="250" id="random_points" name="random_points" min="0" max="50000" step="50" oninput="this.nextElementSibling.value = this.value;"/>
                    <output class='param-text'>250</output>
                </div>`;
        return pointDiv;
    }

    const pointChoice = L.control({ position: 'bottomleft'});
    pointChoice.onAdd = () => {
        const choiceDiv = L.DomUtil.create('div', 'choice-wrapper');
        choiceDiv.innerHTML = `
            <legend class="slide-legend">Points Distribution:</legend>
            <div class='slidecontainer'>
            <div>   
                <input type="radio" class='radio inputs' id="gen_uniform" name="distribution" value="uniform"/>Uniform
            </div>
                <div>
                    <input type="radio" class='radio inputs' id="gen_gaussian" name="distribution" value="gaussian" checked />
                    <label for="gen_gaussian">Gaussian</label>
                </div>
                <div>
                    <input type="radio" class='radio inputs' id="gen_roads" name="distribution" value="roads" />
                    <label for="gen_roads">Roads</label>
                </div>
            </div>`;
        return choiceDiv;
    }

    const voronoiSlider = L.control({ position: 'bottomleft'});
    voronoiSlider.onAdd = () => {
        const vorDiv = L.DomUtil.create('div', 'voronoi-wrapper');
        vorDiv.innerHTML = `
                <legend class="slide-legend">Voronoi Generation</legend>
                <div class='slidecontainer'>
                    <input type="range" class='slider inputs' value="3" id="vor_number" name="vor_number" min="3" max="64" step="1" oninput="this.nextElementSibling.value = this.value;"/>
                    <output class='param-text'>3</output>
                </div>`;
        return vorDiv;
    }

    const readoutWindow = L.control({ position: 'topleft'});
    readoutWindow.onAdd = () => {
        const readoutDiv = L.DomUtil.create('div', 'readout-wrapper');
        readoutDiv.innerHTML = `
            <div class='readout' id='readout-panel' hidden>
                Placeholder text
            </div>`;
        return readoutDiv;
    }; 

    //bottom left stuff
    voronoiSlider.addTo(map);
    disableDragging(voronoiSlider);
    ratioSlider.addTo(map);
    disableDragging(ratioSlider);
    pointSlider.addTo(map);
    disableDragging(pointSlider);
    pointChoice.addTo(map);
    disableDragging(pointChoice);


    readoutWindow.addTo(map);
    disableDragging(readoutWindow); 

    // ****************** Output Readout *************************
        // Readout stuff
    const generationInfo = L.control({ position: 'bottomleft'});
    generationInfo.onAdd = () => {
        const infoDiv = L.DomUtil.create('div', 'geninfo-wrapper');
        var mydict = getParams()
        infoDiv.innerHTML = `
            <legend class='slide-legend'>Layer Info</legend>
            <div class='slidecontainer gen-info' id='gen-info'>
            <table>
                <tr>
                    <th>Total Points</th>
                    <th>Primary Points</th>
                    <th>Secondary Points</th>
                    <th>Points Split</th>
                    <th>No. Voronoi</th>
                    <th>Avg. Points per Voronoi<th>
                    <th>Boundary Area</th>
                </tr>
                <tr>
                    <td>${document.getElementById('random_points').value}</td>
                    <td>${Math.round(document.getElementById('random_points').value * (document.getElementById('points_split').value/100))}
                    <td>${document.getElementById('random_points').value - (Math.round(document.getElementById('random_points').value * (document.getElementById('points_split').value/100)))}
                    <td>${document.getElementById('points_split').value}% primary, ${100 - document.getElementById('points_split').value}% secondary </td>
                    <td>${document.getElementById('vor_number').value}</td>
                    <td>${Math.ceil((document.getElementById('random_points').value - (Math.round(document.getElementById('random_points').value * (document.getElementById('points_split').value/100)))) / (document.getElementById('vor_number').value))}</td>
                    <td>${(polyArea / 1000000).toFixed(2)}km2</td>
                </tr>
            </table>
            </div>`;
        return infoDiv;
    };
    //(pointGroup.getLayers().length < 1) ? 0 : pointGroup.getLayers()[0].getLayers().length
    function refreshInfo() {
        generationInfo.remove(map);
        generationInfo.addTo(map);
        disableDragging(generationInfo);   
    };

    var webinputs = document.getElementsByClassName('inputs');
    console.log(webinputs)
    for(var i = 0; i < webinputs.length; i++) {
        webinputs[i].addEventListener('input', function (e) {
            refreshInfo();
        })
    };

    generationInfo.addTo(map);
    disableDragging(generationInfo); 

    // ************************* topright **********************************
    var roadTimeStart;
    var roadTimeEnd;
    const getRoads = L.control({ position: 'topright'});
    getRoads.onAdd = () => {
        const roadDiv = L.DomUtil.create('div', 'getroad-wrapper');
        roadDiv.innerHTML = `
            <div class="tooltip">
                <span class="tooltiptext tooltip-left">Retrieve road network</span>
                <button class='button btn-icon' title='Retrieve road network'><i class='fa-solid fa-road'></i></button>
            </div>`;
        roadDiv.addEventListener('click', () => {
            roadTimeStart = Date.now();

            if(polyGroup.getLayers().length > 0) {
                if((polyArea / 1000000) < areaLimit) {
                    $.ajax({
                        url: "/getroads",
                        type: "POST",
                        contentType: "application/json",
                        data: JSON.stringify({
                            'data' : polyGroup.toGeoJSON(),
                            'params' : getParams()
                        }),
                            success: function(response){
                                console.log("roads", JSON.parse(response['roads']))
                                lineGroup.clearLayers()
                                L.geoJSON(JSON.parse(response['roads'])).addTo(lineGroup)
                                roadTimeEnd = Date.now() - roadTimeStart;
                                console.log(`Road generation - Time taken = ${roadTimeEnd / 1000} seconds`);
                            },
                            error: function(response){
                                console.log("we dun goofed")
                            }
                    });
                } else {
                    readoutMessage("Area is too large. Area limit is 2km^2.");
                    return
                }
            } else {
                readoutMessage("Please load/draw an area boundary before generating a dataset.");
                return;
            }
        });
        return roadDiv;
    }

    var roadPointTimeStart;
    var roadPointTimeEnd;
    const getRoadPoints = L.control({ position: 'topright'});
    getRoadPoints.onAdd = () => {
        const roadDiv = L.DomUtil.create('div', 'getroadpoints-wrapper');
        roadDiv.innerHTML = `
            <div class="tooltip">
                <span class="tooltiptext tooltip-left">Get road points</span>
                <button class='button btn-icon' title='Get road points'><i class='fa-solid fa-road'></i>+</button>
            </div>`;
        roadDiv.addEventListener('click', () => {
            roadPointTimeStart = Date.now();
            if(getParams()['bound_type'] == 1) {
                $.ajax({
                    url: "/roadpoints",
                    type: "POST",
                    contentType: "application/json",
                    data: JSON.stringify({
                        'data' : lineGroup.toGeoJSON(),
                        'params' : getParams()
                    }),
                        success: function(response){
                            if (pointGroup.getLayers().length > 0) {
                                pointGroup.clearLayers();
                            }
                            console.log("plotting points", JSON.parse(response['points']))
                            L.geoJSON(JSON.parse(response['points']), {
                                pointToLayer: function (feature, latlng) {
                                    return L.circleMarker(latlng, geojsonMarkerOptions);
                                }
                            }).addTo(pointGroup)
                            roadPointTimeEnd = Date.now() - roadPointTimeStart;
                            console.log(`Road Point generation - Time taken = ${roadPointTimeEnd / 1000} seconds`);
                            console.log("added points", roadPointTimeEnd / 1000)
                            
                        },
                        error: function(response){
                            console.log("we dun goofed")
                        }
                });
            } else {
                alert("Roads must be retrieved from drawn polygons.")
                readoutMessage("Please load/draw an area boundary before generating a dataset.");
                return;
            }
        });
        return roadDiv;
    }

    // Visualizing voronoi
    const generateVoronoi = L.control({ position: 'topright' });
    generateVoronoi.onAdd = () => {
        const genVorDiv = L.DomUtil.create('div', 'genvoronoi-wrapper');
        genVorDiv.innerHTML = `
            <div class="tooltip">
                <span class="tooltiptext tooltip-left">Generate voronoi polygons</span>
                <button class='button btn-icon' title='Generate voronoi'><i class='fa-solid fa-scissors'></i></button>
            </div>`;
        genVorDiv.addEventListener('click', () => {
            if(getParams()['vor_number'] > 0) {
                function getCentroid(){
                    if (markersGroup.getLayers().length < 1) {
                        return L.marker(polyGroup.getBounds().getCenter()).addTo(markersGroup);
                    } 
                    else {
                        return markersGroup.getLayers()[0];
                    }    
                }
                console.log("starting ajax query")
                $.ajax({
                    url: "/voronoi",
                    type: "POST",
                    contentType: "application/json",
                    data: JSON.stringify({
                        'data' : polyGroup.toGeoJSON(),
                        'params' : getParams(),
                        'centroid' : getCentroid().toGeoJSON()                    
                    }),
                        success: function(response){
                            console.log("let's get it")
                            if (vorGroup.getLayers().length > 0) {
                                vorGroup.clearLayers();
                            }
                            //console.log("response", JSON.parse(response))
                            L.geoJSON(JSON.parse(response)).addTo(vorGroup)
                        },
                        error: function(response){
                            console.log("we dun goofed")
                        }
                    });
                console.log("done.")
            } else {
                console.log("zero voronoi selected.")
                readoutMessage("Set a value with the Voronoi slider to use them in the points generation.", 5000);
            }
        });
        return genVorDiv;
    };

    var pointTimeStart;
    var pointTimeEnd;
    const generateButton = L.control({ position: 'topright' });
    generateButton.onAdd = () => {
        const genDiv = L.DomUtil.create('div', 'genbutton-wrapper');
        genDiv.innerHTML = `
            <div class="tooltip">
                <span class="tooltiptext tooltip-left">Generate dataset</span>
                <button class='button btn-icon' id='btn-generate' title='Generate data'><i class='fa-solid fa-wand-magic-sparkles'></i></button>
            </div>
                `;
        genDiv.addEventListener('click', () => {
            pointTimeStart = Date.now();

            console.log("number of polys is=", polyGroup.getLayers().length);
            if(polyGroup.getLayers().length == 0) {
                readoutMessage("Please load/draw an area boundary before generating a dataset.");
                return;
            }
            if(getParams()['num_points'] > 0) {
                // Road distribution
                if(getParams()['gen_type'] == 2) {
                    if(lineGroup.getLayers().length > 0) {
                        $.ajax({
                            url: "/roadpoints",
                            type: "POST",
                            contentType: "application/json",
                            data: JSON.stringify({
                                'data' : lineGroup.toGeoJSON(),
                                'params' : getParams()
                            }),
                                success: function(response){
                                    if (pointGroup.getLayers().length > 0) {
                                        pointGroup.clearLayers();
                                    }
                                    console.log("plotting points", JSON.parse(response['points']))
                                    L.geoJSON(JSON.parse(response['points']), {
                                        pointToLayer: function (feature, latlng) {
                                            return L.circleMarker(latlng, geojsonMarkerOptions);
                                        }
                                    }).addTo(pointGroup)
                                    console.log("added points")
                                    pointTimeEnd = Date.now() - pointTimeStart;
                                    console.log(`Point generation - Time taken = ${pointTimeEnd / 1000} seconds`);
                                },
                                error: function(response){
                                    console.log("we dun goofed")
                                }
                        });
                    } else {
                        readoutMessage("Please load the road network for your loaded region.");
                    }
                // Uniform or Gaussian points  
                } else {
                    console.log('generate data');
                    document.getElementById('btn-generate').disabled = true;
                    console.log(getParams())
                    function getCentroid(){
                        if (markersGroup.getLayers().length < 1) {
                            console.log("test:", L.marker(polyGroup.getBounds().getCenter()));
                            return L.marker(polyGroup.getBounds().getCenter()).addTo(markersGroup);
                        } 
                        else {
                            return markersGroup.getLayers()[0];
                        }    
                    }
                    getCov();
                    $.ajax({
                        url: "/test",
                        type: "POST",
                        contentType: "application/json",
                        data: JSON.stringify({
                            'data' : polyGroup.toGeoJSON(),
                            'params' : getParams(),
                            'centroid' : getCentroid().toGeoJSON(),
                            'voronoi' : vorGroup.getLayers().length > 0 ? vorGroup.toGeoJSON() : null
                        }),
                            success: function(response){
                                if (JSON.parse(response['points']).features.length == 0) {
                                    console.log("no points received.");
                                    readoutMessage("Please check covariance parameters...");
                                    document.getElementById('btn-generate').disabled = false;
                                } else {
                                    if (pointGroup.getLayers().length > 0) {
                                        pointGroup.clearLayers();
                                    }
                                    L.geoJSON(JSON.parse(response['points']), {
                                        pointToLayer: function (feature, latlng) {
                                            return L.circleMarker(latlng, geojsonMarkerOptions);
                                        }
                                    }).addTo(pointGroup)
                                    if('voronoi' in response) {
                                        if (vorGroup.getLayers().length < 1) {
                                            vorGroup.clearLayers()
                                            L.geoJSON(JSON.parse(response['voronoi'])).addTo(vorGroup);
                                        }
                                    }
                                    refreshInfo()
                                    console.log("points:", pointGroup.getLayers()[0].getLayers().length)
                                    document.getElementById('btn-generate').disabled = false;
                                    document.getElementById('btn-download').disabled = false;
                                    readoutMessage(getParams());
                                    pointTimeEnd = Date.now() - pointTimeStart;
                                    console.log(`Point generation - Time taken = ${pointTimeEnd / 1000} seconds`);
                                }
                            }
                    });
                } 

            } else {
                console.log("no points value.");
                readoutMessage("Please select a points value with the points slider.");
            }
        });
        return genDiv;
    };

    const clearButton = L.control({ position: 'topright'});
    clearButton.onAdd = () => {
        const clearDiv = L.DomUtil.create('div', 'clearbutton-wrapper');
        clearDiv.innerHTML = `
        <div class="tooltip">
            <span class="tooltiptext tooltip-left">Clear map data</span>
            <button class='button btn-icon' id='btn-clear' title='Clear data'><i class='fa-solid fa-xmark'></i></button>
        </div>
        `;
        clearDiv.addEventListener('click', () => {
            console.log('clear data')
            readoutMessage("Data cleared.");
            pointGroup.clearLayers();
            vorGroup.clearLayers();
            document.getElementById('btn-generate').disabled = false;
        });
        return clearDiv;
    }


    function saveLayer(layerGroup) {
        var geoJSON = layerGroup.toGeoJSON();
        var file = 'filename' + '.geojson';
        saveAs(new File([JSON.stringify(geoJSON)], file, {
            type: "text/plain;charset=utf-8"
        }), file);
    }

    const downloadButton = L.control({ position: 'topright'});
    downloadButton.onAdd = () => {
        const downDiv = L.DomUtil.create('div', 'download-wrapper');
        downDiv.innerHTML = `
            <div class="tooltip">
                <span class="tooltiptext tooltip-left">Download dataset</span>
            <button class='button btn-icon' id='btn-download' title='Download data'><i class='fa-solid fa-download'></i></button>
            </div>
            `;
        downDiv.addEventListener('click', () => {
            console.log('download data');
            document.getElementById('btn-download').disabled = true;
            saveLayer(pointGroup);
            document.getElementById('btn-download').disabled = false;
        });
        return downDiv;
    }


    var varSettings = "";

    function updateChoice() {
        if(document.getElementById('var_choice').value == "int") {
            document.getElementById('meta_options').innerHTML = `
                <div>
                    <label for="start_int_range">Min</label>
                    <input type='number' id='range_a' name='start_int_range' placeholder='0'>
                </div>
                <div>
                    <label for="end_int_range">Max</label>
                    <input type='number' id='range_b' name='end_int_range' placeholder='9999'>
                </div>
            `;            
        } else if (document.getElementById('var_choice').value == "str") {
            document.getElementById('meta_options').innerHTML = `
                <div>
                    <label for="str_len">String length</label>
                    <input type='number' name='str_len' id='str_len' value='1'>
                </div>
            `;
        } else if (document.getElementById('var_choice').value == "ts") {
            document.getElementById('meta_options').innerHTML = `
                <div>
                    <label for="start_ts_range">Start date</label>
                    <input type='datetime-local' name='start_ts_range' id='range_a' value="2025-01-01T00:00">
                </div>
                <div>
                    <label for="end_ts_range">End date</label>
                    <input type='datetime-local' name='start_ts_range' id='range_b' value="2025-12-31T23:59">
                </div>
            `;
        } else if (document.getElementById('var_choice').value == "regex") {
            document.getElementById('meta_options').innerHTML = `
                <div>
                    <label for="regex_var">Regular Expression</label>
                    <input type='text' id='regex_var' name='regex_var' placeholder='\\d{3}-\\d{4}-[aeiou]{3}'>
                </div>
            `;
        } else {
            document.getElementById('meta_options').innerHTML = "none";
        }
    };

    const metaChoice = L.control({ position: 'bottomright'});
    metaChoice.onAdd = () => {
        const metaDiv = L.DomUtil.create('div', 'meta-wrapper');
        metaDiv.innerHTML = `
                <legend class="slide-legend">Metadata</legend>
                <div class='slidecontainer slide-long'>
                    <label for="variable">Choose a datatype:</label>
                    <select name="variable" id="var_choice">
                        <option value="int">Integer</option>
                        <option value="str">String</option>
                        <option value="ts">Timestamp</option>
                        <option value="regex">Regular Expression</option>
                    </select>
                    <div id='meta_options'></div>
                    <div>
                        <label for="var_name">Variable Name</label>
                        <input type='text', name='var_name' id='var_name' placeholder='varname'>
                    </div>
                    <div><input id='var_button_add' type='button' value='Add variable'><input id='var_button_remove' type='button' value='Remove variable'></div>
                    <div><input id='button_gen_metadata' type='button' value='Generate metadata' disabled></div>
                </div>`;
        return metaDiv;
    }

    const metaReadout = L.control({ position: 'bottomright'});
    metaReadout.onAdd = () => {
        const metaReadDiv = L.DomUtil.create('div', 'meta-list-wrapper');
        metaReadDiv.innerHTML = `
                <legend class="slide-legend">Attributes</legend>
                <div class='slidecontainer slide-long'>
                    <table class='metadata-table'>
                        <tr>
                            <th>Variable Name</th>
                            <th>Variable Type</th>
                            <th>Settings</th>
                            <th>Correlation<th>
                        </tr>
                    </table>
                </div>
        `;
        return metaReadDiv;
    }


    const covReadout = L.control({ position: 'bottomright'});
    covReadout.onAdd = () => {
        const covReadDiv = L.DomUtil.create('div', 'meta-list-wrapper');
        covReadDiv.innerHTML = `
                <legend class="slide-legend">Covariance Matrix</legend>
                <div class='slidecontainer slide-long'>
                    <table id='covariance-table'>
                        <tr>
                            <td>var(y)<input type="text" id="var_y" value=${+polyVar_y}></td>
                            <td>cov(yx)<input type="text" id="covar_yx" value=${+polyCovarXY}></td>
                        </tr>
                        <tr>
                            <td>cov(yx)<input type="text" id="covar_yx" value=${+polyCovarXY}></td>
                            <td>var(x)<input type="text" id="var_x" value=${+polyVar_x}></td>
                        </tr>
                    </table>
                </div>
        `;
        return covReadDiv;
    }

    function setCov() {
        document.getElementById('var_y').value = polyVar_y**2;
        document.getElementById('var_x').value = polyVar_x**2;
        document.getElementById('covar_yx').value = polyCovarXY;
        polyCoVar = [
            [polyVar_y, polyCovarXY],
            [polyCovarXY, polyVar_x]
        ]
    };

    function getCov() {
        polyVar_y = document.getElementById('var_y').value;
        polyVar_x = document.getElementById('var_x').value;
        polyCovarXY = document.getElementById('covar_yx').value;
        polyCoVar = [
            [polyVar_y, polyCovarXY],
            [polyCovarXY, polyVar_x]
        ]
    }


    //top right stuff
    generateButton.addTo(map);
    disableDragging(generateButton);
    generateVoronoi.addTo(map);
    disableDragging(generateVoronoi);
    getRoads.addTo(map);
    disableDragging(getRoads);
    clearButton.addTo(map);
    disableDragging(clearButton);
    downloadButton.addTo(map);
    disableDragging(downloadButton);
    metaChoice.addTo(map);
    disableDragging(metaChoice);
    
    document.getElementById('var_choice').addEventListener('change', function (e) {
        updateChoice();
    });
    updateChoice();

    metaReadout.addTo(map);
    disableDragging(metaReadout);
    var varNumber = 0
    // sample listing for metadata attributes

    covReadout.addTo(map);
    disableDragging(covReadout);

    document.getElementById('covariance-table').addEventListener('change', function (e) {
        console.log("values changed");
        getCov();
    });


    document.getElementById('var_button_add').addEventListener('click', function (e) {
        varNumber++;
        var table = document.getElementsByClassName('metadata-table')[0]
        var row = table.insertRow(varNumber);
        row.class = 'metaRow'
        var varChoice = document.getElementById('var_choice').value;
        var varName = document.getElementById('var_name').value
        var varSettings = [];

        if(varChoice == 'int' || varChoice == 'ts') {
            varSettings.push(document.getElementById('range_a').value.replace('T', ' '));
            varSettings.push(document.getElementById('range_b').value.replace('T', ' '));
        } else if(varChoice == 'str') {
            varSettings.push(document.getElementById('str_len').value);
        } else if(varChoice == 'regex') {
            varSettings.push(document.getElementById('regex_var').value);
        }
        
        metaCol = {type: varChoice, name: varName, params: varSettings}
        metaDict.push(metaCol);
        console.log(metaDict);
        row.innerHTML = `
            <td>${varName}</td>
            <td>${varChoice}</td>
            <td>${"(" + varSettings + ")"}</td>
            <td><input type="radio" id=${"var"+varNumber} name="auto_corr" value=${varName}></td>
        `;
        document.getElementById('button_gen_metadata').disabled = false;
    });
    
    document.getElementById('var_button_remove').addEventListener('click', function (e) {
        if(varNumber > 0 ) {
            var table = document.getElementsByClassName('metadata-table')[0];
            table.deleteRow(varNumber);
            varNumber--;
            metaDict.pop();
            console.log(metaDict);
            if(varNumber == 0) {
                document.getElementById('button_gen_metadata').disabled = true;
            }
        }
    });

    function toDateTime(secs) {
        var t = new Date(1970, 0, 1); // Epoch
        t.setSeconds(secs);
        return t;
    }
    var metaDataTimeStart;
    var metaDataTimeEnd;
    document.getElementById('button_gen_metadata').addEventListener('click', function (e) {
        metaDataTimeStart = Date.now();
        if(pointGroup.getLayers().length > 0) {
            if(varNumber > 0) {
                
                $.ajax({
                    url: "/metadata",
                    type: "POST",
                    contentType: "application/json",
                    data: JSON.stringify({
                        'data' : pointGroup.toGeoJSON(),
                        'params' : metaDict
                    }),
                        success: function(response){
                            if (pointGroup.getLayers().length > 0) {
                                pointGroup.clearLayers();
                            }
                            // get indexs of the timestamp variables
                            var tsIndex = []
                            for (var col of metaDict) {
                                if (col['type'] == 'ts') {
                                    tsIndex.push(col['name'])
                                }
                            }
                            var dataDict = JSON.parse(response['points'])
                            
                            //for (var row of dataDict['features']) {
                            //    for (var index of tsIndex) {
                            //        dataDict['features'][row]['properties'][index] = toDateTime(row['properties'][index]);
                            //    }
                            //

                            for (let i in dataDict['features']) {
                                for (var index of tsIndex) {
                                    dataDict['features'][i]['properties'][index] = toDateTime(dataDict['features'][i]['properties'][index])
                                }
                            }

                            console.log(dataDict['features'][0]['properties'])                            
                            L.geoJSON(dataDict, {
                                pointToLayer: function (feature, latlng) {
                                    //console.log(feature.properties)
                                    return L.circleMarker(latlng, geojsonMarkerOptions);
                                }
                            }).addTo(pointGroup);
                            console.log("added points with metadata")
                            metaDataTimeEnd = Date.now() - metaDataTimeStart;
                            console.log(`Metadata generation - Time taken = ${metaDataTimeEnd / 1000} seconds`)
                        },
                        error: function(response){
                            console.log("we dun goofed")
                        }
                });
            }
        } else {
            errMsg = "A dataset must be generated first before metadata can be added."
            console.log(errMsg);
            readoutMessage(errMsg);
        }
        
    });

    function formatMeta(dict) {
        var i = 0;
        var metaTable = document.createElement("table");
        var metaHead = metaTable.insertRow(0);
        var metaRow = metaTable.insertRow(1);
        for (var key in dict) {
            var cellHead = metaHead.insertCell(i);
            cellHead.innerHTML = `${key}`;
            var cell = metaRow.insertCell(i++);
            cell.innerHTML = `${dict[key]}`
        }
        return metaTable;
    };


    var layerPopup;
    pointGroup.on('mouseover', function(e){
        var pointMeta = e.layer.feature.properties
        var coordinates = e.layer.feature.geometry.coordinates;
        var swapped_coordinates = [coordinates[1], coordinates[0]];  //Swap Lat and Lng
        if (map) {
            layerPopup = L.popup()
            .setLatLng(swapped_coordinates)
            .setContent(formatMeta(pointMeta))
                .openOn(map);            
        }
    });
    pointGroup.on('mouseout', function (e) {
        if (layerPopup && map) {
            map.closePopup(layerPopup);
            layerPopup = null;
        }
    });

    function readoutMessage(msg, time=5000) {
        document.getElementById('readout-panel').innerHTML = msg;
        $('#readout-panel').hide().fadeIn(400);
        $('#readout-panel').delay(time).fadeOut(400);
    }

    let welcomeMessage = `
        Welcome to RADIAN! A Python-based tool for generating synthetic spatial datasets\n
        To start, search for a city/country boundary, then hit the magic wand to generate a dataset!
    `;
    readoutMessage(welcomeMessage);
});
