
function disabledEventPropagation(event)
    {
   if (event.stopPropagation) {
       event.stopPropagation();
}
else if(window.event) {
   window.event.cancelBubble=true;
   }
   }
function hidePopups() {
    $(".glyphicon").popover("hide"), container.style.display = "none", container2.style.display = "none",container3.style.display = "none", closer.blur()
}
function panPopupIntoView(e) {
    var a = {
            width: popupOverlay.getElement().clientWidth + 50,
            height: popupOverlay.getElement().clientHeight + 50
        },
        o = map.getSize(),
        r = 30,
        t = 290,
        n = a.width - t + 30,
        p = popupOverlay.getOffset(),
        s = map.getPixelFromCoordinate(e),
        i = s[0] - t,
        l = o[0] - (s[0] + n),
        u = s[1] - a.height + p[1],
        c = o[1] - (s[1] + r) - p[1],
        _ = view.getCenter(),
        d = map.getPixelFromCoordinate(_);
    0 > l ? d[0] -= l : 0 > i && (d[0] += i), 0 > u ? d[1] += u : 0 > c && (d[1] -= c);
    var g = ol.animation.pan({
        duration: 1e3,
        source: view.getCenter()
    });
    map.beforeRender(g), view.setCenter(map.getCoordinateFromPixel(d))
}
function showPopupEventHandler(e, featureinfoUrl) {
    $(".glyphicon").popover("hide");
    showPopupAtCoordinates(e.coordinate[0], e.coordinate[1])
}
function showPopupAtCoordinates(e, a) {
    coord = [e, a];
    //EPSG:3011 = SWEREF99
    //EPSG:4326 = WGS84

    
    var point = ol.proj.transform(coord, map.getView().getProjection(), 'EPSG:3011');

    var restParams = SOLCONFIG.restSourceQ.params;
    restParams.geometry = point.join(','); // sätt koordinaten här

    var queryUrl = SOLCONFIG.restSourceQ.url + '?' + new URLSearchParams(restParams).toString();

    var url = "/Umbraco/surface/PlantData/GetRoofInfo?getFeatureinfoUrl=" + encodeURIComponent(queryUrl);

    $.getJSON(url, function (data) {

        if (data.features && data.features.length > 0) {
            var attrs = data.features[0].attributes;

            updatePopupContentsFromGetFeatureInfo(attrs);

            popupOverlay.setPosition(coord);
            container.style.display = "block";
            container.style.visibility = "visible";
            panPopupIntoView(coord);

            //make pages inside popup start with page1 if new popup is created
            document.getElementById("customPopupDiv1").style.display = "block";
            document.getElementById("customPopupDiv2").style.display = "none";
            document.getElementById("customPopupDiv3").style.display = "none";

        }
     })
     .fail(function (jqXHR, textStatus, errorThrown) {
            console.log("error " + textStatus);
            console.log("incoming Text " + jqXHR.responseText);
            console.log(errorThrown);
     })
}
function addPin(e, a) {
    var pic_element = $('<img id="pin" src="/img/pin.png" data-toggle="tooltip" title="' + a + '"/>')
        .on('click', function (e) {
             $(".location-popover").not(this).popover('hide');
            disabledEventPropagation(e);
});

    view.setZoom(ZOOM_LEVEL_FOR_SEARCH), view.setCenter([Math.round(e.X), Math.round(e.Y)]), map.addOverlay(new ol.Overlay({
        position: [e.X, e.Y],
        offset: [-12, -30],
        stopEvent: !1,
        element: pic_element
    })), $('[data-toggle="tooltip"]').tooltip({
        container: "body"
    })
}
function significant(e, a) {
    if (0 == e)
        return 0;
    var o = Math.ceil(Math.log(e) / Math.LN10),
        r = Math.pow(10, a - o),
        t = Math.round(e * r);
    return Math.round(t / r)
}
function formatNumber(e, a) {
    if (isNaN(e))
        return "0";
    e = significant(e, 3);
    var o = new RegExp("(-?[0-9]+)([0-9]{3})"),
        r = e + "";
    for (void 0 === a && (a = " "); o.test(r);)
        r = r.replace(o, "$1" + a + "$2");
    return r
}
function updatePopupContentsFromGetFeatureInfo(data) {
    newData = Object();
    newData.takyta = Number(data.takyta);
    newData.takyta_a = Number(data.takyta_a);
    newData.tak_1000 = Number(data.tak_1000);
    newData.tak_950_10 = Number(data.tak_950_10);
    newData.tak_950 = Number(data.tak_950);
    newData.tot_sol = Number(data.tot_sol);
    newData.tot_sol_a = Number(data.tot_sol_a);
    newData.sol_1000 = Number(data.sol_1000);
    newData.sol_950_10 = Number(data.sol_950_10);
    newData.sol_950 = Number(data.sol_950);
    newData.id_f = data.id_f;
    updatePopupContents(newData)
}
function updatePopupContents(e) {
    energyData = e;
    $("#popup-area-total").text(formatNumber(e.takyta_a)),
    $("#popup-energy-total").text(formatNumber(e.tot_sol_a));
    $("#popup-area-c1").text(formatNumber((e.tak_1000 * 0.8)));
    $("#popup-area-c2").text(formatNumber((e.tak_950_10 * 0.8)));
    $("#popup-area-c3").text(formatNumber((e.tak_950 * 0.8)));
    $("#popup-area-c3-2").text(formatNumber((e.tak_950 * 0.8)));
    $("#popup-input-area2-c1").val(Math.round(.8 * e.tak_1000));
    $("#popup-input-area2-c2").val(Math.round(.8 * e.tak_950_10));
    onEditPopupFields()
}
function onEditPopupFields(e) {
    var a = .8,
        o = .8;

        $("#popup-input-area2-c1").val() != (.8 * energyData.tak_1000) && (a = $("#popup-input-area2-c1").val() / energyData.tak_1000),
        $("#popup-input-area2-c2").val() != (.8 * energyData.tak_950_10) && (o = $("#popup-input-area2-c2").val() / energyData.tak_950_10),

        a > .8 && (a = .8),
        o > .8 && (o = .8),

        //High
        $("#popup-input-area2-c1").val() > Math.round(.8 * energyData.tak_1000) ? ($("#popup-input-area2-c1").parent().addClass("has-error"),
        $("#popup-input-area2-c1").parent().parent().parent().addClass("danger"),
        e && "popup-input-area2-c1" == e.target.id && $('[data-toggle="tooltip_c1"]').attr("title", "Max " + Math.round(.8 * energyData.tak_1000) + " m2").tooltip("fixTitle").tooltip("show"),
        $("#popup-energy-c1").text(formatNumber(.8 * energyData.tak_1000 * energyData.sol_1000 * .144)),
        $("#popup-heat-c1").text(formatNumber(.8 * energyData.tak_1000 * energyData.sol_1000 * .5))) : ($("#popup-input-area2-c1").parent().removeClass("has-error"),
        $("#popup-input-area2-c1").parent().parent().parent().removeClass("danger"),
        //$('[data-toggle="tooltip_c1"]').tooltip("destroy"),
        $("#popup-energy-c1").text(formatNumber(energyData.tak_1000 * energyData.sol_1000 * a * .144)),
        $("#popup-heat-c1").text(formatNumber(energyData.tak_1000 * energyData.sol_1000 * a * .5))),
        //console.log("Calculation High: area " + a * energyData.tak_1000 + " * solpotential " + energyData.sol_1000 + " * 0.144");

        //Med
        $("#popup-input-area2-c2").val() > Math.round(.8 * energyData.tak_950_10) ? ($("#popup-input-area2-c2").parent().addClass("has-error"),
        $("#popup-input-area2-c2").parent().parent().parent().addClass("danger"),
        e && "popup-input-area2-c2" == e.target.id && $('[data-toggle="tooltip_c2"]').attr("title", "Max " + Math.round(.8 * energyData.tak_950_10) + " m2").tooltip("fixTitle").tooltip("show"),
        $("#popup-energy-c2").text(formatNumber(.8 * energyData.tak_950_10 * energyData.sol_950_10 * .144)),
        $("#popup-heat-c2").text(formatNumber(.8 * energyData.tak_950_10 * energyData.sol_950_10 * .5))) : ($("#popup-input-area2-c2").parent().removeClass("has-error"),
        $("#popup-input-area2-c2").parent().parent().parent().removeClass("danger"),
        //$('[data-toggle="tooltip_c2"]').tooltip("destroy"),
        $("#popup-energy-c2").text(formatNumber(energyData.tak_950_10 * energyData.sol_950_10 * o * .144)),
        $("#popup-heat-c2").text(formatNumber(energyData.tak_950_10 * energyData.sol_950_10 * o * .5))),
        //console.log("Calculation Med: area " + o * energyData.tak_950_10 + " * solpotential " + energyData.sol_950_10 + " * 0.144");

        //co2
        $("#popup-co2-el").text(formatNumber(((energyData.tak_1000 * energyData.sol_1000 * a * .144) + (energyData.tak_950_10 * energyData.sol_950_10 * o * .144)) * 0.1)),
        $("#popup-co2-varme").text(formatNumber(((energyData.tak_1000 * energyData.sol_1000 * a * .5) + (energyData.tak_950_10 * energyData.sol_950_10 * o * .5)) * 0.1))
}

    proj4.defs("EPSG:5850", "+proj=tmerc +lat_0=0 +lon_0=18 +k=1 +x_0=150000 +y_0=0 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +vunits=m +no_defs"),
    proj4.defs("EPSG:3011", "+proj=tmerc +lat_0=0 +lon_0=18 +k=1 +x_0=150000 +y_0=0 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs"),
    proj4.defs("EPSG:3857", "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs"),
    proj4.defs("EPSG:900913", "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs");

var GWCPROJ = ol.proj.get("EPSG:3857"),
    SWEREF99 = ol.proj.get("EPSG:3011"),
    distanceMapWmsSource = new ol.source.TileWMS(SOLCONFIG.distanceMapWmsSource),
    closeupMapWmsSource = new ol.source.TileWMS(SOLCONFIG.closeupMapWmsSource),
    roofSource = new ol.source.TileArcGISRest(SOLCONFIG.roofSource),
    ZOOM_LEVEL_FOR_BACK2 = 18,
    ZOOM_LEVEL_FOR_SEARCH = 18,
    distanceMapWmsLayer = new ol.layer.Tile({
        source: distanceMapWmsSource
    }),
    closeupMapWmsLayer = new ol.layer.Tile({
        source: closeupMapWmsSource,
        visible: !1
    }),
    roofColoringWmsLayer = new ol.layer.Tile({
        source: roofSource,
    }),

    bounds = [135e3, 6565e3, 165e3, 6595e3],
    container = document.getElementById("popup"),
    content = document.getElementById("popup-content"),
    closer = document.getElementById("popup-closer"),
    closer2 = document.getElementById("popup2-closer"),
    container2 = document.getElementById("popup2"),
    closer3 = document.getElementById("popup3-closer"),
    container3 = document.getElementById("popup3");
closer.onclick = function() {
    return hidePopups(), !1
};
closer2.onclick = function () {
    return hidePopups(), !1
};
closer3.onclick = function () {
    return hidePopups(), !1
};

window.app = {};
var app = window.app;

view = new ol.View({
    projection: SWEREF99,
    displayProjection: SWEREF99,
    center: [152715, 6579781],
    maxZoom: 19,
    minZoom: 12,
    zoom: 12,
    extent: bounds
})
var element = document.getElementById('popup2');
var tooltip = document.getElementById('tooltip');
//element was container below 
var popupOverlay = new ol.Overlay({
    element: container,
    offset: [-290, -300]
});
var popupOverlay2 = new ol.Overlay({
    element: element,
    offset: [0, -10]
});
var tooltippOverlay = new ol.Overlay({
    element: tooltip,
    offset: [10, 0],
    positioning: 'bottom-left'
});

map = new ol.Map({
    logo:false,
    controls: ol.control.defaults({
        attributionOptions: /** @type {olx.control.AttributionOptions} */ ({
            collapsible: false
        })
    }),

    layers: [distanceMapWmsLayer, closeupMapWmsLayer, roofColoringWmsLayer],
            target: "map",
    view: view,
    overlays: [popupOverlay, popupOverlay2, tooltippOverlay]
});

zoomslider = new ol.control.ZoomSlider, map.addControl(zoomslider), map.getView().fitExtent(bounds, map.getSize()), map.getView().on("change:resolution", function () {
    view.getZoom() >= ZOOM_LEVEL_FOR_BACK2 ? (distanceMapWmsLayer.setVisible(!1), closeupMapWmsLayer.setVisible(!0)) : (distanceMapWmsLayer.setVisible(!0), closeupMapWmsLayer.setVisible(!1))
});


map.on('click', function (evt) {
    var feature = map.forEachFeatureAtPixel(evt.pixel,
        function (feature, layer) {
            return feature;
        });
    if (feature) {  
        popupOverlay2.setPosition(evt.coordinate);
        container2.style.display = "block";
        panPopupIntoView(evt.coordinate);
        $("#popup2-title").text(feature.get('name'));
        var refurl = feature.get('refurl');
        $("#popup2-ref").attr('href', refurl);
        $("#popup2-owner").text('\xC4gare: ' + feature.get('owner'));
        $("#popup2-fastighet").text('Fastighet:' + feature.get('fastighet'));
        $("#popup2-yta").text('Solcellsyta:' + feature.get('yta')+ ' m\xB2');

        var daySum = getYearSum(feature.get('id'));
        //Hide tooltip
        tooltip.style.display = 'none';
        //Hide popup3
        container3.style.display = 'none';
        container.style.display = 'none';

    } else {
  /*      $(element).popover('destroy');*/
        container2.style.display = 'none';
        container3.style.display = 'none';
        showPopupEventHandler(evt);
    }
});

map.on("pointerdrag",
    function () {
    $(".glyphicon").popover("hide")
    });

map.on('pointermove', displayTooltip);

function displayTooltip(evt) {
    var pixel = evt.pixel;
    var feature = map.forEachFeatureAtPixel(pixel, function (feature) {
        return feature;
    });
    tooltip.style.display = feature ? '' : 'none';
    if (feature) {
        tooltippOverlay.setPosition(evt.coordinate);
        tooltiptext.innerHTML = feature.get('name');
    }
};



var searchAddr = function(e) {
        hidePopups();
        var a = SOLCONFIG.URL_TO_WEBQUERY_ADDRESS + encodeURIComponent(e);
        $.ajax({
            type: "GET",
            url: a,
            dataType: "json",
            xhr: window.IEXMLHttpRequest || jQuery.ajaxSettings.xhr,
            crossDomain: !0,
            success: function(e) {
                $("#pin").remove(), $.each(e.dbrows, function(e, a) {
                    return 0 === e && addPin(a, a.STREET + " " + a.NUM), 1 === e ? !1 : void 0
                })
            }
        })
    },
    searchProp = function(e) {
        hidePopups();
        var a = SOLCONFIG.URL_TO_WEBQUERY_PROPERTY + encodeURIComponent(e);
        $.ajax({
            type: "GET",
            url: a,
            dataType: "json",
            xhr: window.IEXMLHttpRequest || jQuery.ajaxSettings.xhr,
            crossDomain: !0,
            success: function(e) {
                $("#pin").remove(), $.each(e.dbrows, function(e, a) {
                    return 0 === e && addPin(a, a.TRAKT + " " + a.FBETNR), 1 === e ? !1 : void 0
                })
            }
        })
    };
$("#searchForm").submit(function(e) {
    searchAddr($("#searchString")[0].value), e.preventDefault();
    searchProp($("#searchString")[0].value), e.preventDefault();
});

var energy_org_c1,
    energy_org_c2,
    area_org_c1,
    area_org_c2;

var redstyle = new ol.style.Style({
    image: new ol.style.Circle({
        radius: 6,
        stroke: new ol.style.Stroke({
            color: 'black',
            width: 1
        }),
        fill: new ol.style.Fill({
            color: '#FF0000'
        })
    })
});

var greenstyle = new ol.style.Style({
    image: new ol.style.Circle({
        radius: 6,
        stroke: new ol.style.Stroke({
            color: 'black',
            width: 1
        }),
        fill: new ol.style.Fill({
            color: '#33FF33'
        })
    
    }),
  
});

var yellowstyle = new ol.style.Style({
    image: new ol.style.Circle({
        radius: 6,
        stroke: new ol.style.Stroke({
            color: 'black',
            width: 1
        }),
        fill: new ol.style.Fill({
            color: '#FCD15C'
        })
    })
});
var orangestyle = new ol.style.Style({
    image: new ol.style.Circle({
        radius: 6,
        stroke: new ol.style.Stroke({
            color: 'black',
            width: 1
        }),
        fill: new ol.style.Fill({
            color: '#FF8000'
        })
    })
});

var greystyle = new ol.style.Style({
    image: new ol.style.Circle({
        radius: 6,
        stroke: new ol.style.Stroke({
            color: 'black',
            width: 1
        }),
        fill: new ol.style.Fill({
            color: '#A0A0A0'
        })
    })
});
var vectorSource = new ol.source.Vector();

var vectorLayer = new ol.layer.Vector({
    source: vectorSource
});
map.addLayer(vectorLayer);
$(document).ready(function () {

    $.getJSON("/Umbraco/surface/Features/GetFeatures", function (locationArray) {

        for (var i = 0; i < locationArray.length; i++) {

            var location = locationArray[i];

            var coord = [location.geolocation.longitude,location.geolocation.latitude];
            //EPSG:3011 = SWEREF99
            //EPSG:4326 = WGS84
            var o = ol.proj.transform(coord, "EPSG:4326", "EPSG:3011");

            var feature = new ol.Feature({
                geometry: new ol.geom.Point([o[0], o[1]]),
                name: location.name,
                id: location.id,
                owner: location.owner,
                key: location.key,
                refurl: location.url,
                fastighet: location.fastighet,
                yta: location.yta
            });
            feature.setStyle(orangestyle);
            vectorSource.addFeature(feature);

        };
    });

    $('[data-toggle="popover"]').popover({
        container: "body"
    }), $("input.popup-input").on("keyup", function(e) {
        onEditPopupFields(e)
    }), $("input").each(function() {
        "" == $(this).val() && "" != $(this).attr("placeholder") && ($(this).val($(this).attr("placeholder")), $(this).focus(function() {
            $(this).val() == $(this).attr("placeholder") && $(this).val("")
        }), $(this).blur(function() {
            "" == $(this).val() && $(this).val($(this).attr("placeholder"))
        }))
    }), $.support.cors = !0

    $(document).ready(function () {
        $('[data-toggle="takytapopover"]').popover();
    });

    $("#searchForm").keydown(function (e) {
        if (!e) e = window.event;
        var keyCode = e.keyCode || e.which;
        if (keyCode == '13') {
            // Enter pressed
            searchAddr($("#searchString")[0].value), e.preventDefault();
            searchProp($("#searchString")[0].value), e.preventDefault();
            return false;
        }
    });
    $(window).trigger('resize');
    map.updateSize();
});

$(".legendInfo").on("click", function (e) {
    e.preventDefault();
    container3.style.display = 'block';
    container2.style.display = 'none';
});


$(window).resize(function () {
    var canvasheight = $('#map').parent().css('height');
    var canvaswidth = $('#map').parent().css('width');

    $('#map').css("height", canvasheight);
    $('#map').css("width", canvaswidth);

    $('#map').css('height', $(window).height());
});

function getYearSum(id) {

    $.ajax({
        url: "/Umbraco/surface/Solel/GetEnergyThisYear",
        type: "GET",
        dataType: 'json',
        data: {
            'plantId': id
        }
    })
    .done(function (result) {
        if (result != null)
        {
            $("#popup2-energy").text('Producerat i \xE5r: ' + result.value.toFixed() + ' ' + result.unit);
        }
        else
        {
            $("#popup2-energy").text('Producerat i \xE5r: 0 Wh');
        }
    })
    .fail(function (result) {
        alert(result.d);
    })
}

//solkartan custom code
function customPopupTab(tabNo) {
    if (tabNo == 2) {
        document.getElementById("customPopupDiv1").style.display = "none";
        document.getElementById("customPopupDiv2").style.display = "block";
        document.getElementById("customPopupDiv3").style.display = "none";
    }
    else if (tabNo == 1) {
        document.getElementById("customPopupDiv1").style.display = "block";
        document.getElementById("customPopupDiv2").style.display = "none";
        document.getElementById("customPopupDiv3").style.display = "none";
    }
    else {
        document.getElementById("customPopupDiv1").style.display = "none";
        document.getElementById("customPopupDiv2").style.display = "none";
        document.getElementById("customPopupDiv3").style.display = "block";
    }
}

