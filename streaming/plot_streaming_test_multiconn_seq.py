import sys
import subprocess
import os
import glob
import json
import pickle
import statistics
import numpy
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

QUALITY_BANDWIDTH = {
    "144p": [94963, 217648],
    "240p": [217649, 406269],
    "360p": [406270, 750191],
    "480p": [750192, 1538170],
    "720p": [1538171, 2898540],
    "1080p": [2898541, 8608822],
    "1440p": [8608823, 2898540],
    "2160p": [2898541, 9999999]
}
FIVE_QUALITY_COLOR = ["#ffffe5", "#fff7bc", "#fee391", "#fec44f", "#fe9929"]


def sort_quality_change(video_qualities):
    if not video_qualities:
        return [], []
    quality_change = {}

    current_start_timestamp = video_qualities[0][1]
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

    quality_colors = FIVE_QUALITY_COLOR[-len(sorted_quality_change_keys):]

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

    if quality_colors:
        mymap = matplotlib.colors.ListedColormap(quality_colors)
        Z = [[0, 0], [0, 0]]
        min, max = (0, len(quality_colors))
        step = 1
        levels = range(min, max + step, step)
        CS3 = plt.contourf(Z, levels, cmap=mymap)
        cbar = plt.colorbar(CS3, orientation="horizontal", pad=0.4)
        cbar.ax.set_xticklabels(sorted_quality_change_keys)

    plt.ylabel('buffered (s)')
    plt.xlabel('time (s)')
    plt.xlim((0, plot_until_time))


def get_pcap_seq_all_conns(pcapFile, server_port=None):
    if server_port is None:
        print('Please provide server Port')
        sys.exit()

    src_port = 'tcp.srcport'

    cmd = ['tshark', '-r', pcapFile, '-T', 'fields', '-E', 'separator=/t', '-e', src_port,
           '-e', 'frame.time_relative', '-e', 'tcp.seq', '-e', 'frame.len', '-e', 'tcp.analysis.retransmission',
           '-e', 'tcp.analysis.out_of_order']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = p.communicate()

    curr_bytes = 0

    bytes_in = []
    seq_in = []
    timestamps_in = []
    seq_re = []
    timestamps_re = []
    for sl in output.splitlines():
        sl = sl.decode("utf-8")
        l = sl.split('\t')
        src_port = l[0]
        try:
            # Out of order
            time = l[1]
            seq = int(l[2])
            frame_len = int(l[3])
            ret = l[4]
            # time relative to the beginning of the connection
            out = l[5]
        except:
            continue

        if src_port == server_port:
            if ret:
                seq_re.append(seq)
                timestamps_re.append(float(time))
            else:
                seq_in.append(seq)
                timestamps_in.append(float(time))
                curr_bytes += frame_len
                bytes_in.append(curr_bytes)
            # curr_bytes += int(len)

    return seq_re, timestamps_re, seq_in, timestamps_in, bytes_in


def index_plot_until(timestamps, until_time):
    index_until = 0
    for timestamp in timestamps:
        if float(timestamp) > float(until_time):
            break
        index_until += 1
    return index_until


def plot_bytes_over_time(seq_re_0, timestamps_re_0, seq_in_0, timestamps_in_0,
                         seq_re_1, timestamps_re_1, seq_in_1, timestamps_in_1,
                         label_0, label_1, plot_until_time):
    # fig, ax1 = plt.subplots(figsize=(20, 8))

    plot_until_second = plot_until_time

    # plot sequence for pcap 0

    plot_until = index_plot_until(timestamps_in_0, plot_until_second)
    plt.plot(timestamps_in_0[:plot_until], seq_in_0[:plot_until], 'o', markerfacecolor="#fb9a99",
             markeredgewidth=3,
             markersize=10, alpha=0.1,
             markeredgecolor="none", label=label_0)

    # plot sequence for pcap 1

    plot_until = index_plot_until(timestamps_in_1, plot_until_second)
    plt.plot(timestamps_in_1[:plot_until], seq_in_1[:plot_until], 'o', markerfacecolor="#a6cee3",
             markeredgewidth=3,
             markersize=10, alpha=0.1,
             markeredgecolor="none", label=label_1)

    # # plot retransmit
    plot_until = index_plot_until(timestamps_re_0, plot_until_second)
    plt.plot(timestamps_re_0[:plot_until], seq_re_0[:plot_until], 'x', markersize=7, markeredgewidth=2,
             c='#e31a1c',
             label="{} retrans".format(label_0))
    #
    plot_until = index_plot_until(timestamps_re_1, plot_until_second)
    plt.plot(timestamps_re_1[:plot_until], seq_re_1[:plot_until], 'x', markersize=7, markeredgewidth=2,
             c='#1f78b4',
             label="{} retrans".format(label_1))

    plt.legend(loc="upper right", markerscale=2, fontsize=5)

    plt.ticklabel_format(style='sci', axis='y', scilimits=(0, 0))
    plt.ylabel('Sequence')
    # plt.title(plot_title)
    plt.xlim((0, plot_until_second))
    plt.tick_params(axis='x', labelsize=0)
    # plt.show()


def load_packet_info(pcap_file_0, pcap_file_1):
    server_port = "80"

    if not (pcap_file_0 and pcap_file_1):
        return False

    seq_re_0, timestamps_re_0, seq_in_0, timestamps_in_0, bytes_in_0 = get_pcap_seq_all_conns(pcap_file_0,
                                                                                              server_port)
    seq_re_1, timestamps_re_1, seq_in_1, timestamps_in_1, bytes_in_1 = get_pcap_seq_all_conns(pcap_file_1,
                                                                                              server_port)

    return seq_re_0, timestamps_re_0, seq_in_0, timestamps_in_0, bytes_in_0, seq_re_1, timestamps_re_1, seq_in_1, timestamps_in_1, bytes_in_1


def plot_test(seq_re_0, timestamps_re_0, seq_in_0, timestamps_in_0,
              seq_re_1, timestamps_re_1, seq_in_1, timestamps_in_1, label_0, label_1,
              plot_until_time):
    loss_rate_0 = round(len(seq_re_0) / len(seq_re_0 + seq_in_0), 5)
    loss_rate_1 = round(len(seq_re_1) / len(seq_re_1 + seq_in_1), 5)

    plot_title = "{} vs {} --{}--{}".format(label_0, label_1, loss_rate_0, loss_rate_1)

    plot_bytes_over_time(seq_re_0, timestamps_re_0, seq_in_0, timestamps_in_0,
                         seq_re_1, timestamps_re_1, seq_in_1, timestamps_in_1,
                         label_0, label_1, plot_until_time)

    return plot_title


def parse_video_stat(video_stat):
    video_stat = json.load(open(video_stat, "r"))

    video_qualities = []
    seconds_buffered = []
    estimated_bandwidths = []
    average_throughputs = []
    initial_ts = video_stat[0]["timestamp"]

    buffering_time = 0
    playing_time = 0

    # prev_time = initial_ts / 1000
    prev_time = video_stat[0]["currentTime"]
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
        estimated_bandwidth = stat["bandwidth"]
        average_throughput = stat["throughput"]

        if current_playtime - prev_time < 0.4:
            buffering_time += (0.5 - (current_playtime - prev_time))
        else:
            playing_time += (current_playtime - prev_time)
            # only consider buffered seconds if video is actually playing
            seconds_buffered.append((buffered, current_time))
            video_qualities.append((quality, current_time))

        prev_time = current_playtime

        estimated_bandwidths.append((estimated_bandwidth, current_time))
        average_throughputs.append((average_throughput, current_time))
        # seconds_buffered.append((buffered, current_time))
        # video_qualities.append((quality, current_time))

    return seconds_buffered, video_qualities, estimated_bandwidths, average_throughputs


def separate_timestamp_and_stat(stat_w_timestamp):
    stats = []
    timestamps = []
    for i in stat_w_timestamp:
        stats.append(i[0])
        timestamps.append(i[1])
    return stats, timestamps


def plot_bandwidth_throughput(estimated_bandwidths, average_throughputs, gputs_0, ts_0, label_0, gputs_1, ts_1, label_1,
                              plot_until_time, video_qualities):
    plt.subplot(3, 1, 2)

    estimated_bandwidths, estimated_bandwidths_ts = separate_timestamp_and_stat(estimated_bandwidths)
    average_throughputs, average_throughputs_ts = separate_timestamp_and_stat(average_throughputs)

    plot_until = index_plot_until(estimated_bandwidths_ts, plot_until_time)
    plt.plot(estimated_bandwidths_ts[:plot_until], estimated_bandwidths[:plot_until], color="#8c2d04", linewidth=2,
             label='Player estimated bandwidth')

    # plot_until = index_plot_until(average_throughputs_ts, plot_until_time)
    # plt.plot(average_throughputs_ts[:plot_until], average_throughputs[:plot_until], color="#d7191c", linewidth=2,
    #          label='Player throughputs')

    plot_until = index_plot_until(ts_0, plot_until_time)
    plt.plot(ts_0[:plot_until], gputs_0[:plot_until], color="#e31a1c", linewidth=2,
             label='{} throughput'.format(label_0))
    plot_until = index_plot_until(ts_1, plot_until_time)
    plt.plot(ts_1[:plot_until], gputs_1[:plot_until], color="#1f78b4", linewidth=2,
             label='{} throughput'.format(label_1))

    sorted_quality = []
    for quality in video_qualities:
        if quality[0] not in sorted_quality:
            sorted_quality.append(quality[0])
    sorted_quality.sort()
    quality_colors = FIVE_QUALITY_COLOR[-len(sorted_quality):]

    quality_count = 0
    for quality in sorted_quality:
        interval = QUALITY_BANDWIDTH[quality]
        plt.axhspan(interval[0], interval[1], facecolor=quality_colors[quality_count], lw=0)
        quality_count += 1

    plt.legend(loc="upper right", markerscale=2, fontsize=5)
    plt.xlim((0, plot_until_time))
    plt.ylabel('Goodput (bps)')
    plt.ticklabel_format(style='sci', axis='y', scilimits=(0, 0))
    plt.tick_params(axis='x', labelsize=0)
    # ax1.xticks([], [])


def get_goodput_from_bytes(bytes, timestamps, client_sampling_interval):
    timeL = [float(x) for x in timestamps]

    xput_interval = client_sampling_interval

    untilT = xput_interval
    lastT = 0
    gputs = []
    ts = []
    for i in range(len(timeL)):
        # Calculate bytes sent during this period
        if timeL[i] >= untilT:
            gputs.append((bytes[i] - bytes[lastT]) / xput_interval)
            lastT = i
            untilT += xput_interval
            ts.append(timeL[i])

    gputs = [x * 8 for x in gputs]

    return gputs, ts


def do_all_plots(pcap0, pcap1, label0, label1, video_stat):
    seconds_buffered, video_qualities, estimated_bandwidths, average_throughputs = parse_video_stat(video_stat)

    last_playing_time = 0
    if seconds_buffered:
        last_playing_time = seconds_buffered[-1][1]

    plt.subplot(3, 1, 1)

    seq_re_0, timestamps_re_0, seq_in_0, timestamps_in_0, bytes_in_0, seq_re_1, timestamps_re_1, seq_in_1, timestamps_in_1, bytes_in_1 = load_packet_info(
        pcap0, pcap1)

    plot_until_time = max(last_playing_time, timestamps_in_0[-1], timestamps_in_1[-1])

    plot_title = plot_test(seq_re_0, timestamps_re_0, seq_in_0, timestamps_in_0,
                           seq_re_1, timestamps_re_1, seq_in_1, timestamps_in_1, label0, label1,
                           plot_until_time)

    gputs_0, ts_0 = get_goodput_from_bytes(bytes_in_0, timestamps_in_0, 0.5)
    gputs_1, ts_1 = get_goodput_from_bytes(bytes_in_1, timestamps_in_1, 0.5)

    plot_bandwidth_throughput(estimated_bandwidths, average_throughputs, gputs_0, ts_0, label0, gputs_1, ts_1, label1,
                              plot_until_time, video_qualities)

    plt.subplot(3, 1, 3)
    plot_bufferedbytes_quality(video_qualities, seconds_buffered, plot_until_time)
    # plt.tight_layout()
    plt.savefig('{}/{}.png'.format("./", plot_title), dpi=400)
    plt.close()


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

    do_all_plots(pcap0, pcap1, label0, label1, video_stat)


if __name__ == "__main__":
    main()
