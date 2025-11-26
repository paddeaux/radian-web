$(document).ready(function(){
    var marker;
    var disableMarker = false;
    var map = L.map('map').fitWorld();
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
            circle: false
        },
        edit: {
            featureGroup: drawnGroup,
            edit: false
        }
    });

    map.on("draw:created", function (e) {
        console.log(e.layerType)
        if (e.layerType == 'rectangle') {
            drawnGroup.clearLayers();
            drawnGroup.addLayer(e.layer);
            document.getElementById('radio_poly_drawn').disabled = false;
        }
        if (e.layerType == 'marker') {
            markersGroup.clearLayers();
            markersGroup.addLayer(e.layer);
        }
        
    });

    map.on("draw:deleted", function (e) {
        drawnGroup.clearLayers()
        document.getElementById('radio_poly_drawn').disabled = true;
        document.getElementById('radio_poly_boundary').checked = true;
    })

    map.addControl(drawControl);



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
        } else {
            gen_type = 0;
        }
        if (document.getElementById("radio_poly_drawn").checked) {
            bound_type = 1;
        } else {
            bound_type = 0
        }
        console.log("testing:", +document.getElementById("points_split").value)
        return {
            "num_points" : +document.getElementById("random_points").value,
            "gen_type" : +gen_type,
            "vor_number" : +document.getElementById("vor_number").value,
            "points_split": +document.getElementById("points_split").value,
            "bound_type": +bound_type,
            "road_offset": 5 // need to set UI slider for this
        }
    }
 
    // Function to stop mag dragging when mouse is near a control input
    function disableDragging(controlObj) {
        controlObj.getContainer().addEventListener('mouseover', function () {
            map.dragging.disable();
            disableMarker = true;
        });

        // Re-enable dragging when user's cursor leaves the element
        controlObj.getContainer().addEventListener('mouseout', function () {
            map.dragging.enable();
            disableMarker = false;
        });
    }

    // Custom button panels

    // bottomleft
    const searchBar = L.control({ position: 'bottomleft' });
    searchBar.onAdd = () => {
        const barDiv = L.DomUtil.create('div', 'searchbar-wrapper');
    barDiv.innerHTML = `
        <div class="tooltip">
            <span class="tooltiptext tooltip-search">Specify a location within which to generate data</span>
        <input type="text" value="Dublin, Ireland" id="location" required>
        `;
        return barDiv;
    };
    searchBar.addTo(map);
    disableDragging(searchBar);

    // Loading boundary button
    const searchButton = L.control({ position: 'bottomleft' });
    searchButton.onAdd = () => {
        const buttonDiv = L.DomUtil.create('div', 'button-wrapper');
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
                console.log("geojson is:", geojsonFeature);
                map.fitBounds(polyGroup.getBounds());
            })
            document.getElementById('btn-generate').disabled = false;
            document.getElementById('btn-zoom').disabled = false;
            document.getElementById("btn-map-load").disabled = false;
        });
        return buttonDiv;
    };
    searchButton.addTo(map)
    disableDragging(searchButton);

    // Zoom to boundary button
    const zoomBoundary = L.control({ position: 'bottomleft' });
    zoomBoundary.onAdd = () => {
        const zoomDiv = L.DomUtil.create('div', 'zoom-wrapper');
        zoomDiv.innerHTML = `
            <div class="tooltip">
                <span class="tooltiptext tooltip-home">Zoom to boundary</span>
                <button class='button btn-icon home-btn' id='btn-zoom' title='Zoom to boundary' disabled><i class='fa-solid fa-house'></i></button>
            </div>
                `;
        zoomDiv.addEventListener('click', () => {
            console.log("zooming to data")
            map.fitBounds(polyGroup.getBounds());
        });
        return zoomDiv;
    };
    zoomBoundary.addTo(map);
    disableDragging(zoomBoundary);

    // ************************* topright **********************************

    const getRoads = L.control({ position: 'topright'});
    getRoads.onAdd = () => {
        const roadDiv = L.DomUtil.create('div', 'getroad-wrapper');
        roadDiv.innerHTML = `
            <div class="tooltip">
                <span class="tooltiptext tooltip-left">Retrieve road network</span>
                <button class='button btn-icon' title='Retrieve road network'><i class='fa-solid fa-road'></i></button>
            </div>`;
        roadDiv.addEventListener('click', () => {
            if(getParams()['bound_type'] == 1) {
                $.ajax({
                    url: "/getroads",
                    type: "POST",
                    contentType: "application/json",
                    data: JSON.stringify({
                        'data' : drawnGroup.toGeoJSON(),
                        'params' : getParams()
                    }),
                        success: function(response){
                            console.log("roads", JSON.parse(response['roads']))
                            lineGroup.clearLayers()
                            L.geoJSON(JSON.parse(response['roads'])).addTo(lineGroup)
                        },
                        error: function(response){
                            console.log("we dun goofed")
                        }
                });
            } else {
                readoutMessage("Please load/draw an area boundary before generating a dataset.");
                return;
            }
        });
        return roadDiv;
    }

    const getRoadPoints = L.control({ position: 'topright'});
    getRoadPoints.onAdd = () => {
        const roadDiv = L.DomUtil.create('div', 'getroadpoints-wrapper');
        roadDiv.innerHTML = `
            <div class="tooltip">
                <span class="tooltiptext tooltip-left">Get road points</span>
                <button class='button btn-icon' title='Get road points'><i class='fa-solid fa-road'></i>+</button>
            </div>`;
        roadDiv.addEventListener('click', () => {
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
                            console.log("added points")
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
            console.log("number of polys is=", polyGroup.getLayers().length);
            if (document.getElementById("radio_poly_boundary").checked){
                genGroup = polyGroup;
            } else {
                genGroup = drawnGroup;
            }
            if(polyGroup.getLayers().length == 0 && drawnGroup.getLayers().length == 0) {
                readoutMessage("Please load/draw an area boundary before generating a dataset.");
                return;
            }
            if(getParams()['num_points'] > 0) {
                console.log('generate data');
                document.getElementById('btn-generate').disabled = true;
                console.log(getParams())
                function getCentroid(){
                    if (markersGroup.getLayers().length < 1) {
                        console.log("test:", L.marker(polyGroup.getBounds().getCenter()));
                        return L.marker(polyGroup.getBounds().getCenter()).addTo(markersGroup);
                    } 
                    else {
                        console.log("goodbye:", markersGroup)
                        return markersGroup.getLayers()[0];
                    }    
                }
                
                $.ajax({
                    url: "/test",
                    type: "POST",
                    contentType: "application/json",
                    data: JSON.stringify({
                        'data' : genGroup.toGeoJSON(),
                        'params' : getParams(),
                        'centroid' : getCentroid().toGeoJSON(),
                        'voronoi' : vorGroup.getLayers().length > 0 ? vorGroup.toGeoJSON() : null             
                    }),
                        success: function(response){
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
                            document.getElementById('btn-generate').disabled = false;
                            document.getElementById('btn-download').disabled = false;
                            readoutMessage(getParams());
                        }
                    });
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

    // ***************************  bottomright  ************************************
    const ratioSlider = L.control({ position: 'bottomright'});
    ratioSlider.onAdd = () => {
        const ratioDiv = L.DomUtil.create('div', 'ratio-wrapper');
        ratioDiv.innerHTML = `
                        <legend>Points Ratio</legend>
                <div class='slidecontainer'>
                    <input type="range" class='slider' value="50" id="points_split" name="points_split" min="0" max="100" step="1" oninput="this.nextElementSibling.value = this.value"/>
                    <output class='param-text'>50</output>%
                </div>`;
        return ratioDiv;
    }

    const pointSlider = L.control({ position: 'bottomright'});
    pointSlider.onAdd = () => {
        const pointDiv = L.DomUtil.create('div', 'point-wrapper');
        pointDiv.innerHTML = `
            <legend>Number of Points</legend>
                <div class='slidecontainer'>
                    <input type="range" class='slider' value="250" id="random_points" name="random_points" min="0" max="5000" step="50" oninput="this.nextElementSibling.value = this.value"/>
                    <output class='param-text'>250</output>
                </div>`;

        return pointDiv;
    }

    const polyChoice = L.control({ position: 'bottomright'});
    polyChoice.onAdd = () => {
        const choiceDiv = L.DomUtil.create('div', 'polychoice-wrapper');
        choiceDiv.innerHTML = `
            <legend>Polygon Layer</legend>
            <div class='slidecontainer'>
                <input type="radio" class='radio' id="radio_poly_boundary" name="poly-type" value="boundary" checked />
                <label for="gen_uniform">Loaded Boundary</label><br>
                <input type="radio" class='radio' id="radio_poly_drawn" name="poly-type" value="drawn" disabled/>
                <label for="gen_gaussian">Drawn Polygon</label>
            </div>`;
        return choiceDiv;
    }

    const pointChoice = L.control({ position: 'bottomright'});
    pointChoice.onAdd = () => {
        const choiceDiv = L.DomUtil.create('div', 'choice-wrapper');
        choiceDiv.innerHTML = `
            <legend>Points Distribution:</legend>
            <div class='slidecontainer'>
                <input type="radio" class='radio' id="gen_uniform" name="distribution" value="uniform" checked />
                <label for="gen_uniform">Uniform</label>
                <input type="radio" class='radio' id="gen_gaussian" name="distribution" value="gaussian" />
                <label for="gen_gaussian">Gaussian</label>
            </div>`;
        return choiceDiv;
    }

    const voronoiSlider = L.control({ position: 'bottomright'});
    voronoiSlider.onAdd = () => {
        const vorDiv = L.DomUtil.create('div', 'voronoi-wrapper');
        vorDiv.innerHTML = `
                <legend>Voronoi Generation</legend>
                <div class='slidecontainer'>
                    <input type="range" class='slider' value="3" id="vor_number" name="vor_number" min="3" max="64" step="1" oninput="this.nextElementSibling.value = this.value;"/>
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
    // ordering of UI/buttons

    //top right stuff
    generateButton.addTo(map);
    disableDragging(generateButton);
    generateVoronoi.addTo(map);
    disableDragging(generateVoronoi);
    getRoads.addTo(map);
    disableDragging(getRoads);
    getRoadPoints.addTo(map);
    disableDragging(getRoadPoints);
    clearButton.addTo(map);
    disableDragging(clearButton);
    downloadButton.addTo(map);
    disableDragging(downloadButton);

    //bottom right stuff
    ratioSlider.addTo(map);
    disableDragging(ratioSlider);
    pointSlider.addTo(map);
    disableDragging(pointSlider);
    polyChoice.addTo(map)
    disableDragging(polyChoice);
    pointChoice.addTo(map);
    disableDragging(pointChoice);
    voronoiSlider.addTo(map);
    disableDragging(voronoiSlider);
    readoutWindow.addTo(map);
    disableDragging(readoutWindow);  

    function readoutMessage(msg, time=5000) {
        document.getElementById('readout-panel').innerHTML = msg;
        $('#readout-panel').hide().fadeIn(400);
        $('#readout-panel').delay(time).fadeOut(400);
    }

    // Readout stuff
    const generationInfo = L.control({ position: 'bottomright'});
    generationInfo.onAdd = () => {
        const infoDiv = L.DomUtil.create('div', 'geninfo-wrapper');
        var mydict = getParams()
        infoDiv.innerHTML = `
            <div class='slidecontainer' id='gen-info'>
            <table>
                <tr>
                    <th>Total Points</th>
                    <th>Gen. Type</th>
                    <th>No. Voronoi</th>
                    <th>Point Split</th>
                </tr>
                <tr>
                    <td>${mydict['num_points']}</td>
                    <td>${mydict['gen_type']}</td>
                    <td>${mydict['vor_number']}</td>
                    <td>${mydict['points_split']}</td>
                </tr>
            </table>
            </div>`;
        return infoDiv;
    };
    generationInfo.addTo(map);
    disableDragging(generationInfo);  

    function refreshInfo() {
        generationInfo.remove(map);
        generationInfo.addTo(map);
        disableDragging(generationInfo);   
    };

    // blah blah olena is terrible 
    function infoListeners() {
        document.getElementById('random_points').addEventListener('input', (evt) => {
            refreshInfo();
        });
        document.getElementById('points_split').addEventListener('input', (evt) => {
            refreshInfo();
        });
        document.getElementById('vor_number').addEventListener('input', (evt) => {
            refreshInfo();
        });
    }
    
    infoListeners()
    let welcomeMessage = `
        Welcome to RADIAN! A Python-based tool for generating synthetic spatial datasets\n
        To start, search for a city/country boundary, then hit the magic wand to generate a dataset!
    `;
    readoutMessage(welcomeMessage);
});
