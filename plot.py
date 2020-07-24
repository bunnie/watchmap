#!/usr/bin/python3
from xml.dom import minidom
import matplotlib
import matplotlib.cm as cm
import folium

def _get_gpx_text(track, tagname, type="str"):
    """Grab text from a given track."""
    tag_txt = []
    tag = track.getElementsByTagName(tagname)
    for i in tag:
        for child in i.childNodes:
            if child.nodeType == child.TEXT_NODE:
                if type == "float":
                    tag_txt.append(
                        float(child.data)
                    )
                else:
                    tag_txt.append(
                        child.data
                    )
    return tag_txt

def _get_gpx_attribute(track, attribute):
    tag_txt = []
    tag = track.getElementsByTagName('trkpt')
    for t in tag:
        tag_txt.append(
            float(t.getAttribute(attribute))
        )
    return tag_txt

def read_gpx_file(gpxfile, maxpulse=187):
    gpx = minidom.parse(gpxfile)
    tracks = gpx.getElementsByTagName('trk')
    for track in tracks:
        track.getElementsByTagName('trkseg')
        track_data = {
            'speed': _get_gpx_text(track, 'speed', 'float'),
            'elevation': _get_gpx_text(track, 'ele'),
            'time': _get_gpx_text(track, 'time'),
            'lat': _get_gpx_attribute(track, 'lat'),
            'lon': _get_gpx_attribute(track, 'lon'),
        }
        yield track_data

def plot_osm_map(track):
    speeds = track['speed']
    minima = min(speeds)
    maxima = max(speeds)

    norm = matplotlib.colors.Normalize(vmin=minima, vmax=maxima, clip=True)
    mapper = cm.ScalarMappable(norm=norm, cmap=cm.plasma)
    m = folium.Map(location=[track['lat'][0], track['lon'][0]], zoom_start=15)
    for index in range(len(track['lat'])):
        if track['speed'][index] == 0:
            track['speed'][index] = 0.01
        folium.CircleMarker(
            location=(track['lat'][index], track['lon'][index]),
            radius=track['speed'][index] * 5.0,
            tooltip=str(track['speed'][index]),
            fill_color=matplotlib.colors.to_hex(mapper.to_rgba(track['speed'][index])),
            fill=True,
            fill_opacity=0.2,
            weight=0,
        ).add_to(m)

    m.save('folium.html')


for track in read_gpx_file('2020-07-23-16-19-52-speed.gpx'):
    #fig = plot_speed(track)
    plot_osm_map(track)
