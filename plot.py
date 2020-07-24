#!/usr/bin/python3

import argparse
import subprocess
import os

from xml.dom import minidom
import matplotlib
import matplotlib.cm as cm
import folium

# snippets of the gpx parsing code came from gpxplotter (https://github.com/andersle/gpxplotter)
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

def _get_gpx_hr(track):
    tag_txt = []
    tag = track.getElementsByTagName('gpxtpx:hr')
    for t in tag:
        for child in t.childNodes:
            ext = child.getElementsByTagName('gpxtpx:hr')
            if ext == child.TEXT_NODE:
                tag_txt.append(float(child.data))


def read_gpx_file(gpxfile):
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

def read_hr_bodge(hrfile):
    gpx = minidom.parse(hrfile)
    tracks = gpx.getElementsByTagName('trk')
    for track in tracks:
        track.getElementsByTagName('trkseg')
        track_data = {
            'hr': _get_gpx_text(track, 'gpxtpx:hr', 'float'),
            'lat': _get_gpx_attribute(track, 'lat'),
            'lon': _get_gpx_attribute(track, 'lon'),
        }

    # returns only the last track
    return track_data

def speed_conversion(raw):
    return raw * 1.60934 * 2.0 # convert mph to kph, plus some scaling fudge factor

def plot_osm_map(track, output='speed-map.html', hr=None):
    for i in range(len(track['speed'])):
        track['speed'][i] = speed_conversion(track['speed'][i])
    speeds = track['speed']
    minima = min(speeds)
    maxima = max(speeds)

    norm = matplotlib.colors.Normalize(vmin=minima, vmax=maxima, clip=True)
    mapper = cm.ScalarMappable(norm=norm, cmap=cm.plasma)
    m = folium.Map(location=[track['lat'][0], track['lon'][0]], zoom_start=15)
    for index in range(len(track['lat'])):
        if track['speed'][index] == 0:
            track['speed'][index] = 0.01
        else:
            track['speed'][index] = track['speed'][index]
        if hr:
            try:
                tooltip=str(track['speed'][index]) + ' ' + str(hr['hr'][index]) +'bpm'
            except:
                tooltip=str(track['speed'][index])
        else:
            tooltip=str(track['speed'][index])
        folium.CircleMarker(
            location=(track['lat'][index], track['lon'][index]),
            radius=track['speed'][index]**2 / 8,
            tooltip=tooltip,
            fill_color=matplotlib.colors.to_hex(mapper.to_rgba(track['speed'][index])),
            fill=True,
            fill_opacity=0.2,
            weight=0,
        ).add_to(m)

    m.save(output)


def plot_osm_hr_map(track, hr_file, output='hr-map.html'):
    for i in range(len(track['speed'])):
        track['speed'][i] = speed_conversion(track['speed'][i])

    hr = hr_file['hr']
    minima = min(hr)
    maxima = max(hr)

    norm = matplotlib.colors.Normalize(vmin=minima, vmax=maxima, clip=True)
    mapper = cm.ScalarMappable(norm=norm, cmap=cm.plasma)
    m = folium.Map(location=[track['lat'][0], track['lon'][0]], zoom_start=15)
    for index in range(len(hr)):
        if track['speed'][index] == 0:
            track['speed'][index] = 0.01
        else:
            track['speed'][index] = track['speed'][index]
        if hr:
            tooltip=str(track['speed'][index]) + ' ' + str(hr[index]) +'bpm'
        else:
            tooltip=str(track['speed'][index])
        folium.CircleMarker(
            location=(track['lat'][index], track['lon'][index]),
            radius=(hr[index] - minima) / 5.0,
            tooltip=tooltip,
            fill_color=matplotlib.colors.to_hex(mapper.to_rgba(hr[index])),
            fill=True,
            fill_opacity=0.2,
            weight=0,
        ).add_to(m)

    m.save(output)

#for track in read_gpx_file('2020-07-23-16-19-52-speed.gpx'):
#    plot_osm_map(track)
"""
  gpsbabel -t -i garmin_fit -x track,speed -f 2020-07-23-16-19-52.fit -o gpx -F 2020-07-23-16-19-52-speed.gpx
  gpsbabel -t -i garmin_fit -f 2020-07-23-16-19-52.fit -o gpx,garminextensions -F 2020-07-23-16-19-52-hr.gpx
"""

def main():
    parser = argparse.ArgumentParser(description="Plot GPX data onto a map")
    parser.add_argument(
        "-f", "--file", help="Input file", required=True, type=str,
    )
    parser.add_argument(
        "-r", "--hr-file", help="Heart rate file (must be gpx)", type=str,
    )
    parser.add_argument(
        "-o", "--output", help="Output map name. Defaults to *-map.html", default='map.html', type=str,
    )

    args = parser.parse_args()
    filename, filextension = os.path.splitext(args.file)
    hr = None
    if filextension == '.fit':
        speedfile='/tmp/speed.gpx'
        hrfile='/tmp/hr.gpx'
        subprocess.call(["gpsbabel", "-t", "-i", "garmin_fit", "-x", "track,speed", "-f", args.file, "-o", "gpx", "-F", speedfile])
        subprocess.call(["gpsbabel", "-t", "-i", "garmin_fit", "-f", args.file, "-o", "gpx,garminextensions", "-F", hrfile])
        hr = read_hr_bodge(hrfile)
    else:
        speedfile=args.file
        if args.hr_file != None:
            hr = read_hr_bodge(args.hr_file)

    for track in read_gpx_file(speedfile):
        if hr:
            plot_osm_map(track, filename + '-speed-' + args.output, hr)
            plot_osm_hr_map(track, hr, filename + '-hr-' + args.output)
        else:
            plot_osm_map(track, filename + '-' + args.output, None)


if __name__ == "__main__":
    main()
