var marker;
var map = L.map('map').fitWorld();
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: 
    '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// a layer group, used here like a container for markers
var markersGroup = L.layerGroup();
var polyGroup = L.layerGroup();
var pointGroup = L.layerGroup();
map.addLayer(markersGroup);
map.addLayer(polyGroup);
map.addLayer(pointGroup)

map.on('click', function(e) {
    // get the count of currently displayed markers
    var markersCount = markersGroup.getLayers().length;
    console.log("number of markers:", markersCount);
    if (markersCount < 1) {
        marker = L.marker(e.latlng).addTo(markersGroup);
        console.log("marker coords", marker.getLatLng());
        document.getElementById('output').innerHTML = marker.getLatLng();
        return;
    }
    // remove the markers when MARKERS_MAX is reached
    markersGroup.clearLayers();
});

function drawAdminBoundary() {
  var search_term = document.getElementById("location").value;
  var geojsonFeature;
  console.log(search_term)

      
  var polyCount = polyGroup.getLayers().length;
  console.log("number of polygons:", polyCount);
  
  url = 'https://nominatim.openstreetmap.org/search?q='+search_term+'&polygon_geojson=1&format=jsonv2';
    fetch(url).then(function(response) {
      return response.json();
  })
  .then(function(json) {
    geojsonFeature = json[0].geojson;
    if (polyCount < 1) {
      L.geoJSON(geojsonFeature).addTo(polyGroup);
    }
    else {
      polyGroup.clearLayers();
      L.geoJSON(geojsonFeature).addTo(polyGroup);
    }
    console.log("geojson is:", geojsonFeature);
    $.ajax({
      url: "/test",
      type: "POST",
      contentType: "application/json",
      data: JSON.stringify(JSON.stringify(geojsonFeature))
    });
  });
}

function drawPoints(point_data) {
  console.log(point_data)
  L.geoJSON(point_data).addTo(pointGroup);
}