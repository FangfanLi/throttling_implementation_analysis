import sys
import subprocess
import os
import glob
import json
import pickle
import statistics
import matplotlib

import matplotlib.pyplot as plt
from sklearn.metrics import r2_score

# try:
#     import seaborn as sns
#     sns.set()
# except ImportError:
#     pass

VIDEO_QUALITY_SORTING_MAP = {"144p": 1,
                             "240p": 2,
                             "360p": 3,
                             "480p": 4,
                             "720p": 5,
                             "1080p": 6,
                             "1440p": 7,
                             "2160p": 8
                             }

ALL_QUALITY_COLOR = [
    "#f7fbff",
    "#deebf7",
    "#c6dbef",
    "#9ecae1",
    "#6baed6",
    "#4292c6",
    "#2171b5",
    "#084594"]

FIVE_QUALITY_COLOR = ["#eff3ff", "#bdd7e7", "#6baed6", "#3182bd", "#08519c"]


def sort_quality_change(video_qualities):
    quality_change = {}

    current_start_timestamp = 0
    current_quality = video_qualities[0][0]
    for video_quality_sample in video_qualities:
        if video_quality_sample[0] != current_quality:
            current_quality_interval = [current_start_timestamp, video_quality_sample[1]]
            if current_quality in quality_change:
                quality_change[current_quality].append(current_quality_interval)
            else:
                quality_change[current_quality] = [current_quality_interval]
            current_start_timestamp = video_quality_sample[1]
            current_quality = video_quality_sample[0]

    last_quality_sample = video_qualities[-1]
    if last_quality_sample[1] != current_start_timestamp:
        if current_quality in quality_change:
            quality_change[current_quality].append(
                [current_start_timestamp, last_quality_sample[1]])
        else:
            quality_change[current_quality] = [
                [current_start_timestamp, last_quality_sample[1]]]

    sorted_quality_change_keys = sorted(quality_change.keys(), key=lambda x: VIDEO_QUALITY_SORTING_MAP[x])

    return quality_change, sorted_quality_change_keys


def plot_bufferedbytes_quality(video_qualities, seconds_buffered, plot_until_time):
    quality_change, sorted_quality_change_keys = sort_quality_change(video_qualities)

    quality_colors = FIVE_QUALITY_COLOR[:len(sorted_quality_change_keys)]

    quality_count = 0
    for quality in sorted_quality_change_keys:
        for interval in quality_change[quality]:
            plt.axvspan(interval[0], interval[1], facecolor=quality_colors[quality_count], lw=0)
        quality_count += 1

    seconds_buffered_x = []
    seconds_buffered_y = []
    for buffered in seconds_buffered:
        seconds_buffered_y.append(buffered[0])
        seconds_buffered_x.append(buffered[1])
    plt.plot(seconds_buffered_x, seconds_buffered_y)
    plt.ylabel('buffered (seconds)')
    plt.xlabel('time (s)')

    mymap = matplotlib.colors.ListedColormap(quality_colors)
    Z = [[0, 0], [0, 0]]
    min, max = (0, len(quality_colors))
    step = 1
    levels = range(min, max + step, step)
    CS3 = plt.contourf(Z, levels, cmap=mymap)
    cbar = plt.colorbar(CS3, orientation="horizontal", pad=0.3)
    cbar.ax.set_xticklabels(sorted_quality_change_keys)

    plt.xlim((0, plot_until_time))


def get_pcap_bytes(pcapFile, server_port=None):
    if server_port is None:
        print('Please provide server Port')
        sys.exit()

    src_port = 'tcp.srcport'

    cmd = ['tshark', '-r', pcapFile, '-T', 'fields', '-E', 'separator=/t', '-e', src_port,
           '-e', 'frame.time_relative', '-e', 'frame.len', '-e', 'tcp.analysis.retransmission',
           '-e', 'tcp.analysis.out_of_order']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = p.communicate()

    curr_bytes = 0

    received_bytes_in = []
    timestamps_in = []
    received_bytes_re = []
    timestamps_re = []
    for sl in output.splitlines():
        sl = sl.decode("utf-8")
        l = sl.split('\t')
        src_port = l[0]
        try:
            # Out of order
            time = l[1]
            # Retransmission
            len = l[2]
            # Sequence number
            ret = l[3]
            # time relative to the beginning of the connection
            out = l[4]
        except:
            continue
        if src_port == server_port:
            if ret:
                received_bytes_re.append(curr_bytes)
                timestamps_re.append(float(time))
            else:
                received_bytes_in.append(curr_bytes)
                timestamps_in.append(float(time))
            curr_bytes += int(len)

    return received_bytes_re, timestamps_re, received_bytes_in, timestamps_in


def index_plot_until(timestamps, until_time):
    index_until = 0
    for timestamp in timestamps:
        if float(timestamp) > float(until_time):
            break
        index_until += 1
    return index_until


def plot_bytes_over_time(received_bytes_re_0, timestamps_re_0, received_bytes_in_0, timestamps_in_0,
                                  received_bytes_re_1, timestamps_re_1, received_bytes_in_1, timestamps_in_1, label_0,
                                  label_1, plot_until_time, plot_title=""):
    # fig, ax1 = plt.subplots(figsize=(20, 8))

    plot_until_second = plot_until_time

    # plot sequence for pcap 0
    plot_until = index_plot_until(timestamps_in_0, plot_until_second)

    plt.plot(timestamps_in_0[:plot_until], received_bytes_in_0[:plot_until], 'o', markerfacecolor="#fb9a99",
             markeredgewidth=3,
             markersize=10, alpha=0.1,
             markeredgecolor="none", label=label_0)

    # plot sequence for pcap 1
    plot_until = index_plot_until(timestamps_in_1, plot_until_second)
    plt.plot(timestamps_in_1[:plot_until], received_bytes_in_1[:plot_until], 'o', markerfacecolor="#a6cee3",
             markeredgewidth=3,
             markersize=10, alpha=0.1,
             markeredgecolor="none", label=label_1)

    # plot retransmit
    plot_until = index_plot_until(timestamps_re_0, plot_until_second)
    plt.plot(timestamps_re_0[:plot_until], received_bytes_re_0[:plot_until], 'x', markersize=10, markeredgewidth=5,
             c='#e31a1c',
             label="{} retrans".format(label_0))

    plot_until = index_plot_until(timestamps_re_1, plot_until_second)
    plt.plot(timestamps_re_1[:plot_until], received_bytes_re_1[:plot_until], 'x', markersize=10, markeredgewidth=5,
             c='#1f78b4',
             label="{} retrans".format(label_1))

    plt.legend(loc="upper right", markerscale=2, fontsize=10)
    # ax2.legend(loc='upper right', markerscale=2, fontsize=20)
    plt.ylabel('Bytes transmitted')
    plt.title(plot_title)
    plt.xlim((0, plot_until_second))


def load_packet_info(pcap_file_0, pcap_file_1):
    server_port = "80"

    if not (pcap_file_0 and pcap_file_1):
        return False

    received_bytes_re_0, timestamps_re_0, received_bytes_in_0, timestamps_in_0 = get_pcap_bytes(pcap_file_0,
                                                                                                server_port)
    received_bytes_re_1, timestamps_re_1, received_bytes_in_1, timestamps_in_1 = get_pcap_bytes(pcap_file_1,
                                                                                                server_port)

    return received_bytes_re_0, timestamps_re_0, received_bytes_in_0, timestamps_in_0, received_bytes_re_1, timestamps_re_1, received_bytes_in_1, timestamps_in_1


def plot_test(received_bytes_re_0, timestamps_re_0, received_bytes_in_0, timestamps_in_0, received_bytes_re_1,
              timestamps_re_1, received_bytes_in_1, timestamps_in_1, label_0, label_1, plot_until_time):
    loss_rate_0 = round(len(received_bytes_re_0) / len(received_bytes_in_0 + received_bytes_re_0), 5)
    loss_rate_1 = round(len(received_bytes_re_1) / len(received_bytes_in_1 + received_bytes_re_1), 5)

    plot_title = "{} vs {} --{}--{}".format(label_0, label_1, loss_rate_0, loss_rate_1)

    plot_bytes_over_time(received_bytes_re_0, timestamps_re_0, received_bytes_in_0, timestamps_in_0,
                                  received_bytes_re_1, timestamps_re_1, received_bytes_in_1, timestamps_in_1,
                                  label_0, label_1, plot_until_time, plot_title=plot_title)

    return plot_title


def parse_video_stat(video_stat):
    video_stat = json.load(open(video_stat, "r"))

    video_qualities = []
    seconds_buffered = []
    initial_ts = video_stat[0]["timestamp"]

    for stat in video_stat:
        quality = stat["quality"]
        if not stat["buffered"]:
            buffered_until = 0
        else:
            buffered_until = stat["buffered"][0]["end"]
        current_ts = stat["timestamp"]
        current_time = (current_ts - initial_ts) / 1000
        current_playtime = stat["currentTime"]
        buffered = buffered_until - current_playtime
        seconds_buffered.append((buffered, current_time))
        video_qualities.append((quality, current_time))

    return seconds_buffered, video_qualities


def main():
    try:
        pcap0 = sys.argv[1]
        pcap1 = sys.argv[2]
        label0 = sys.argv[3]
        label1 = sys.argv[4]
        video_stat = sys.argv[5]
    except:
        print(
            '\r\n Please provide the following five inputs: [pcap1] [pcap2] [label1] [label2] [video_stat]')
        sys.exit()

    seconds_buffered, video_qualities = parse_video_stat(video_stat)

    plt.subplot(2, 1, 1)
    received_bytes_re_0, timestamps_re_0, received_bytes_in_0, timestamps_in_0, received_bytes_re_1, timestamps_re_1, received_bytes_in_1, timestamps_in_1 \
        = load_packet_info(pcap0, pcap1)

    plot_until_time = max(seconds_buffered[-1][1], timestamps_in_0[-1], timestamps_in_1[-1])

    plot_title = plot_test(received_bytes_re_0, timestamps_re_0, received_bytes_in_0, timestamps_in_0,
                           received_bytes_re_1, timestamps_re_1, received_bytes_in_1, timestamps_in_1, label0, label1,
                           plot_until_time)

    plt.subplot(2, 1, 2)
    plot_bufferedbytes_quality(video_qualities, seconds_buffered, plot_until_time)
    plt.savefig('{}/{}.png'.format("./", plot_title), dpi=300)


if __name__ == "__main__":
    main()
