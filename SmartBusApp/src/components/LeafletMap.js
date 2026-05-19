/**
 * LeafletMap — OpenStreetMap via WebView, stable (never reloads on state change).
 * Default view: Jhang city centre at street level (zoom 15).
 *
 * Imperative API (via forwardRef):
 *   addBus(id, lat, lng, label)
 *   updateBus(id, lat, lng)
 *   removeBus(id)
 *   setPassenger(lat, lng)
 *   addStops(stops[])          — auto fitBounds to show whole route
 *   setPolyline(coords[])
 *   fitBounds(stops[])
 *   zoomTo(lat, lng, zoom?)
 *   zoomJhang()
 */
import React, { useRef, useImperativeHandle, forwardRef } from 'react';
import { View, StyleSheet } from 'react-native';
import { WebView } from 'react-native-webview';

const JHANG_LAT = 31.2681;
const JHANG_LNG = 72.3178;
const DEFAULT_ZOOM = 15;   // street-level — shows individual roads & localities

const MAP_HTML = `<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=3,user-scalable=yes">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body,#map{width:100%;height:100vh;background:#f2efe9}
.bus-wrap{display:flex;flex-direction:column;align-items:center}
.bus-icon{font-size:32px;line-height:1;filter:drop-shadow(0 2px 5px rgba(0,0,0,.5))}
.bus-label{background:#1A237E;color:#fff;font-size:10px;font-weight:700;padding:2px 6px;border-radius:8px;margin-top:2px;white-space:nowrap}
.you-wrap{display:flex;flex-direction:column;align-items:center}
.you-dot{width:14px;height:14px;background:#1565C0;border:3px solid #fff;border-radius:50%;box-shadow:0 0 0 3px rgba(21,101,192,0.3)}
.you-label{background:#1565C0;color:#fff;font-size:10px;font-weight:700;padding:2px 6px;border-radius:8px;margin-top:3px;white-space:nowrap}
.stop-label{background:rgba(255,255,255,0.92);color:#212121;font-size:10px;font-weight:600;padding:2px 6px;border-radius:6px;border:1px solid #ccc;white-space:nowrap;pointer-events:none}
</style>
</head>
<body>
<div id="map"></div>
<script>
// ── Map init — Jhang street level ─────────────────────────────────────
var map = L.map('map',{
  zoomControl:true,
  attributionControl:true,
  minZoom:10, maxZoom:19
}).setView([${JHANG_LAT},${JHANG_LNG}],${DEFAULT_ZOOM});

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
  maxZoom:19,
  attribution:'&copy; <a href="https://openstreetmap.org">OSM</a>'
}).addTo(map);

// ── State ─────────────────────────────────────────────────────────────
var buses={}, pasMarker=null, polyline=null, stopMarkers=[], routeFitted=false;

// ── Icons ─────────────────────────────────────────────────────────────
function makeBusIcon(label){
  var html='<div class="bus-wrap"><div class="bus-icon">🚌</div>'
           +'<div class="bus-label">'+label+'</div></div>';
  return L.divIcon({html:html,className:'',iconSize:[60,52],iconAnchor:[30,44]});
}
function makeYouIcon(){
  var html='<div class="you-wrap"><div class="you-dot"></div>'
           +'<div class="you-label">You</div></div>';
  return L.divIcon({html:html,className:'',iconSize:[60,36],iconAnchor:[30,10]});
}

// ── Bus ───────────────────────────────────────────────────────────────
function addBus(id,lat,lng,label){
  if(buses[id]){
    buses[id].setLatLng([lat,lng]);
    buses[id].setIcon(makeBusIcon(label));
    return;
  }
  var m=L.marker([lat,lng],{icon:makeBusIcon(label),zIndexOffset:2000})
         .addTo(map).bindPopup('<b>'+label+'</b>');
  buses[id]=m;
  // Fly to bus on first appearance
  map.flyTo([lat,lng],16,{animate:true,duration:1.2});
}

function updateBus(id,lat,lng){
  if(buses[id]){
    // Smoothly glide the bus marker — no camera pan to keep user in control
    buses[id].setLatLng([lat,lng]);
  } else {
    addBus(id,lat,lng,'Bus');
  }
}

function removeBus(id){
  if(buses[id]){map.removeLayer(buses[id]);delete buses[id];}
}

// ── Passenger ─────────────────────────────────────────────────────────
function setPassenger(lat,lng){
  if(pasMarker){
    // Smoothly slide the "You" pin to the new position
    pasMarker.setLatLng([lat,lng]);
    return;
  }
  // First placement: create marker and fly to user's real location
  pasMarker=L.marker([lat,lng],{icon:makeYouIcon(),zIndexOffset:3000})
             .addTo(map).bindPopup('Your Location');
}

// ── Stops ─────────────────────────────────────────────────────────────
function addStops(stops){
  stopMarkers.forEach(function(m){map.removeLayer(m);}); stopMarkers=[];
  if(!stops||!stops.length) return;

  var bounds=[];
  stops.forEach(function(s,i){
    var lat=Number(s.latitude), lng=Number(s.longitude);
    bounds.push([lat,lng]);

    // Colour: green=first, red=last, blue=middle
    var col = i===0 ? '#43A047' : i===stops.length-1 ? '#E53935' : '#1565C0';

    // Circle marker
    var circle=L.circleMarker([lat,lng],{
      radius:9, color:'#fff', weight:2,
      fillColor:col, fillOpacity:1
    }).addTo(map).bindPopup('<b>'+s.stop_name+'</b>'
      +(s.estimated_minutes!=null?'<br>~'+s.estimated_minutes+' min from start':''));
    stopMarkers.push(circle);

    // Permanent stop name label
    var lbl=L.marker([lat,lng],{
      icon:L.divIcon({
        html:'<div class="stop-label">'+s.stop_name+'</div>',
        className:'',
        iconAnchor:[-12,8]
      }),
      interactive:false,
      zIndexOffset:-100
    }).addTo(map);
    stopMarkers.push(lbl);
  });

  // Fit map to show all stops (only on first load, not every refresh)
  if(!routeFitted && bounds.length>0){
    routeFitted=true;
    try{
      map.fitBounds(bounds,{padding:[40,40],maxZoom:16,animate:true});
    }catch(e){}
  }
}

// ── Route polyline ────────────────────────────────────────────────────
function setPolyline(coords){
  if(polyline){map.removeLayer(polyline);polyline=null;}
  if(!coords||coords.length<2) return;
  polyline=L.polyline(coords,{
    color:'#1565C0',weight:5,opacity:0.8,
    dashArray:null,lineJoin:'round',lineCap:'round'
  }).addTo(map);
}

// ── fitBounds to stops ────────────────────────────────────────────────
function fitToStops(){
  if(!stopMarkers.length) return;
  var bounds=[];
  stopMarkers.forEach(function(m){
    if(m.getLatLng) bounds.push([m.getLatLng().lat,m.getLatLng().lng]);
  });
  if(bounds.length>0)
    map.fitBounds(bounds,{padding:[50,50],maxZoom:16,animate:true});
}

// ── Zoom helpers ──────────────────────────────────────────────────────
function zoomTo(lat,lng,zoom){
  map.flyTo([lat,lng],zoom||15,{animate:true,duration:1});
}

// ── Notify RN when ready ──────────────────────────────────────────────
map.whenReady(function(){
  setTimeout(function(){
    if(window.ReactNativeWebView)
      window.ReactNativeWebView.postMessage(JSON.stringify({type:'ready'}));
  },400);
});

// ── Bridge listener ───────────────────────────────────────────────────
function onBridge(e){
  try{ var d=JSON.parse(e.data); if(d&&d.fn) eval(d.fn); }catch(err){}
}
document.addEventListener('message',onBridge);
window.addEventListener('message',onBridge);
</script>
</body>
</html>`;

// ── React component ───────────────────────────────────────────────────────
const LeafletMap = forwardRef(function LeafletMap({ style, onReady }, ref) {
  const webRef = useRef(null);
  const js = (code) => webRef.current?.injectJavaScript(code + '; true;');

  useImperativeHandle(ref, () => ({
    addBus:      (id, lat, lng, label) => js(`addBus(${q(id)},${lat},${lng},${q(label||'Bus')})`),
    updateBus:   (id, lat, lng)        => js(`updateBus(${q(id)},${lat},${lng})`),
    removeBus:   (id)                  => js(`removeBus(${q(id)})`),
    setPassenger:(lat, lng)            => js(`setPassenger(${lat},${lng})`),
    addStops:    (stops)               => js(`addStops(${JSON.stringify(stops)})`),
    setPolyline: (coords)              => js(`setPolyline(${JSON.stringify(coords)})`),
    fitBounds:   ()                    => js(`fitToStops()`),
    zoomTo:      (lat, lng, zoom)      => js(`zoomTo(${lat},${lng},${zoom||15})`),
    zoomJhang:   ()                    => js(`zoomTo(${JHANG_LAT},${JHANG_LNG},15)`),
  }));

  const onMessage = (e) => {
    try {
      const d = JSON.parse(e.nativeEvent.data);
      if (d.type === 'ready' && onReady) onReady();
    } catch (_) {}
  };

  return (
    <View style={[styles.wrap, style]}>
      <WebView
        ref={webRef}
        source={{ html: MAP_HTML }}
        style={styles.wv}
        onMessage={onMessage}
        javaScriptEnabled
        domStorageEnabled
        originWhitelist={['*']}
        mixedContentMode="always"
        scrollEnabled={false}
        bounces={false}
        overScrollMode="never"
        androidLayerType="hardware"
        cacheEnabled
        cacheMode="LOAD_CACHE_ELSE_NETWORK"
      />
    </View>
  );
});

export default LeafletMap;

function q(s) { return JSON.stringify(String(s)); }

const styles = StyleSheet.create({
  wrap: { overflow: 'hidden', backgroundColor: '#f2efe9' },
  wv:   { flex: 1, backgroundColor: 'transparent' },
});
