#!/usr/bin/python3

import argparse
import subprocess
import os

from xml.dom import minidom
import matplotlib
import matplotlib.cm as cm
import folium
from folium.features import DivIcon
from datetime import datetime, timedelta

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

        if hr:
            try:
                tooltip="{:0.1f}kph".format(track['speed'][index]) + ' ' + str(hr['hr'][index]) +'bpm'
            except:
                tooltip="{:0.1f}kph".format(track['speed'][index])
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


def plot_osm_hr_map(track, hr_file, output='hr-map.html', age=45, resting_rate=50, hr_plot_interval=30):
    # speeds will have already been adjusted since we side-effect the global record
#    for i in range(len(track['speed'])):
#        track['speed'][i] = speed_conversion(track['speed'][i])

    maxrate = 220-age
    reserve = maxrate-resting_rate
    rate_table = {
       'resting  ' : [(0.0*reserve + resting_rate, 0.5*reserve + resting_rate), 0],
       'easy     ' : [(0.5*reserve + resting_rate, 0.6*reserve + resting_rate), 0],
       'fatburn  ' : [(0.6*reserve + resting_rate, 0.70*reserve + resting_rate), 0],
       'cardio   ' : [(0.70*reserve + resting_rate, 0.80*reserve + resting_rate), 0],
       'sprint   ' : [(0.80*reserve + resting_rate, 0.90*reserve + resting_rate), 0],
       'anaerobic' : [(0.9*reserve + resting_rate, 1.0*reserve + resting_rate), 0],
    }

    hr = hr_file['hr']
    times = track['time']
    datetimes = []
    for t in times:
        datetimes.append(datetime.strptime(t, '%Y-%m-%dT%H:%M:%SZ'))

    totaltime = (datetimes[-1] - datetimes[0]).total_seconds()

    for i in range(0,len(datetimes) - 1):
        cur_hr = hr[i]
        for name, entry in rate_table.items():
            (hrmin, hrmax) = entry[0]
            if hrmin < cur_hr and hrmax <= cur_hr:
                entry[1] += (datetimes[i+1] - datetimes[i]).total_seconds()

    cum_time = 0 # this is different, because fractional seconds are lost every reading and eventually creates a 2x error!
    for name, entry in rate_table.items():
        cum_time += entry[1]

    for name, entry in rate_table.items():
        (hrmin, hrmax) = entry[0]
        print(name + ' ({:3.0f}-{:3.0f}): '.format(hrmin, hrmax) + str(timedelta(seconds= (entry[1] / cum_time) * totaltime)).split('.')[0] + ' {:.1f}'.format(100.0 * (entry[1] / totaltime)) + '%')

    speeds = track['speed']
    minima = min(speeds)
    maxima = max(speeds)

    norm = matplotlib.colors.Normalize(vmin=minima, vmax=maxima, clip=True)
    mapper = cm.ScalarMappable(norm=norm, cmap=cm.plasma)
    m = folium.Map(location=[track['lat'][0], track['lon'][0]], zoom_start=15)
    elapsed = 0.0
    cur_interval = 0.0
    hr_avg_sum = 0.0
    hr_n = 0
    for index in range(len(hr) - 1):
        elapsed += ( datetime.strptime(track['time'][index+1], '%Y-%m-%dT%H:%M:%SZ') - datetime.strptime(track['time'][index], '%Y-%m-%dT%H:%M:%SZ') ).total_seconds()
        hr_avg_sum += hr[index]
        hr_n += 1
        if elapsed >= cur_interval:
            cur_interval += hr_plot_interval
            folium.map.Marker(
                [track['lat'][index], track['lon'][index]],
                icon=DivIcon(
                    icon_size=(60,12),
                    icon_anchor=(0,0),
                    html='<div style="font-size: 10pt">'+'{:.0f}'.format(hr_avg_sum / hr_n)+'</div>',
                )
            ).add_to(m)
            hr_avg_sum = 0.0
            hr_n = 0

        if track['speed'][index] == 0:
            track['speed'][index] = 0.01

        if hr:
            tooltip="{:0.1f}kph".format(track['speed'][index]) + ' ' + str(hr[index]) +'bpm'
        else:
            tooltip="{:0.1f}kph".format(track['speed'][index])
        folium.CircleMarker(
            location=(track['lat'][index], track['lon'][index]),
            radius=((hr[index] - minima) / 50.0)**2,
            tooltip=tooltip,
            fill_color=matplotlib.colors.to_hex(mapper.to_rgba(speeds[index])),
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
