import sys
import subprocess
import os
import glob
import json
import pickle
import statistics

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


def plot_bufferedbytes_quality(video_qualities, seconds_buffered):

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


def get_pcap_stat(pcapFile, server_port=None):
    if server_port is None:
        print('Please provide server Port')
        sys.exit()

    src_port = 'tcp.srcport'

    cmd = ['tshark', '-r', pcapFile, '-T', 'fields', '-E', 'separator=/t', '-e', src_port, '-e',
           'tcp.analysis.out_of_order',
           '-e', 'tcp.analysis.retransmission',
           '-e', 'tcp.seq', '-e', 'frame.time_relative', '-e', 'tcp.ack']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = p.communicate()

    # All Packets arrived on the server
    arr_all_pList = []
    arr_all_timeList = []

    # Packets arrived on the server in order
    arr_in_pList = []
    arr_in_timeList = []
    # Packets arrived on the server, re transmission
    arr_ret_pList = []
    arr_ret_timeList = []
    # Packets arrived on the server, out-of-order transmission
    arr_out_pList = []
    arr_out_timeList = []

    # All Packets sent from the server
    sent_all_pList = []
    sent_all_timeList = []

    # Packets sent *from* server, in order
    sent_in_pList = []
    sent_in_timeList = []
    # Packets sent *from* server, re transmission
    sent_ret_pList = []
    sent_ret_timeList = []
    # Packets sent *from* server, out-of-order transmission
    sent_out_pList = []
    sent_out_timeList = []

    arr_a_count = 0
    arr_i_count = 0
    arr_r_count = 0
    arr_o_count = 0

    sent_a_count = 0
    sent_i_count = 0
    sent_r_count = 0
    sent_o_count = 0

    for sl in output.splitlines():
        # print(type(sl))
        # sl = str(sl)
        sl = sl.decode("utf-8")
        l = sl.split('\t')
        src_port = l[0]
        # Get the info of this packet
        try:
            # Out of order
            out = l[1]
            # Retransmission
            ret = l[2]
            # Sequence number
            seq = l[3]
            # time relative to the beginning of the connection
            time = l[4]
            # the ack number of this packet
            ack = l[5]
        except:
            continue
        # For packets arrived on the server, record their ack numbers
        # For packets sent from the server, record their sequence numbers

        # For packets sent from the server, put in the sent_* lists
        if src_port == server_port:
            sent_all_pList.append(seq)
            sent_all_timeList.append(time)
            sent_a_count += 1
            if ret:
                sent_ret_pList.append(seq)
                sent_ret_timeList.append(time)
                sent_r_count += 1
            elif out:
                sent_out_pList.append(seq)
                sent_out_timeList.append(time)
                sent_o_count += 1
            else:
                sent_in_pList.append(seq)
                sent_in_timeList.append(time)
                sent_i_count += 1
        # For packets arrived on the server, put in the arr_* lists
        else:
            arr_all_pList.append(ack)
            arr_all_timeList.append(time)
            arr_a_count += 1
            if ret:
                arr_ret_pList.append(ack)
                arr_ret_timeList.append(time)
                arr_r_count += 1
            elif out:
                arr_out_pList.append(ack)
                arr_out_timeList.append(time)
                arr_o_count += 1
            else:
                arr_in_pList.append(ack)
                arr_in_timeList.append(time)
                arr_i_count += 1

    start_timestamp = 0
    start_seq = 0

    arr_all_pList = [float(x) - start_seq for x in arr_all_pList]
    arr_all_timeList = [float(x) - start_seq for x in arr_all_timeList]
    sent_in_pList = [float(x) - start_seq for x in sent_in_pList]
    sent_ret_pList = [float(x) - start_seq for x in sent_ret_pList]
    sent_in_timeList = [float(x) - start_timestamp for x in sent_in_timeList]
    sent_ret_timeList = [float(x) - start_timestamp for x in sent_ret_timeList]

    return sent_in_pList, sent_in_timeList, sent_ret_pList, sent_ret_timeList, sent_all_pList, sent_all_timeList, arr_all_pList, arr_all_timeList, sent_i_count, sent_r_count, sent_a_count, start_timestamp


def plot_throughput_distribution(client_tputs_original, server_tputs_original, plot_carrier_directory, plot_title=""):
    fig, ax = plt.subplots(figsize=(15, 6))

    client_tputs_original.sort()

    client_tputs_original_90 = client_tputs_original[: int(90 * len(client_tputs_original) / 100)]
    server_tputs_original_90 = server_tputs_original[: int(90 * len(client_tputs_original) / 100)]
    interval = max(client_tputs_original_90 + server_tputs_original_90) / float(100)

    bins = []
    for i in range(100):
        bins.append(i * interval)

    plt.hist(client_tputs_original, bins, alpha=0.3, color="#fdbf6f", label="received on client")
    plt.hist(server_tputs_original, bins, alpha=0.3, color="#fb9a99", label="sent from server")

    plt.yscale('log')
    plt.legend(loc='lower right', markerscale=2, fontsize=30)
    plt.xlabel('Throughput (Mbps)')
    plt.ylabel('Number of samples')
    plt.title(plot_title)

    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
                 ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(20)
    plt.tight_layout()
    plt.savefig('{}/throughput_distribution--{}.png'.format(plot_carrier_directory, plot_title))
    plt.close()


def index_plot_until(timestamps, until_time):
    index_until = 0
    for timestamp in timestamps:
        if float(timestamp) > float(until_time):
            break
        index_until += 1
    return index_until


def plot_seq_throughput_over_time(sent_in_timeList_0, sent_in_pList_0, sent_in_timeList_1, sent_in_pList_1,
                       sent_ret_timeList_0, sent_ret_pList_0, sent_ret_timeList_1, sent_ret_pList_1,
                       ack_all_pList_0, ack_all_timeList_0, ack_all_pList_1, ack_all_timeList_1,
                       plot_carrier_directory, label_0, label_1, plot_until_time, plot_title=""):
    # fig, ax1 = plt.subplots(figsize=(20, 8))

    plot_until_second = plot_until_time

    # plot sequence for pcap 0
    plot_until = index_plot_until(sent_in_timeList_0, plot_until_second)
    plt.plot(sent_in_timeList_0[:plot_until], sent_in_pList_0[:plot_until], 'o', markerfacecolor="#fb9a99",
             markeredgewidth=3,
             markersize=15, alpha=0.1,
             markeredgecolor="none", label=label_0)

    # plot sequence for pcap 1
    plot_until = index_plot_until(sent_in_timeList_1, plot_until_second)
    plt.plot(sent_in_timeList_1[:plot_until], sent_in_pList_1[:plot_until], 'o', markerfacecolor="#a6cee3",
             markeredgewidth=3,
             markersize=15, alpha=0.1,
             markeredgecolor="none", label=label_1)

    # plot ACKs
    # plot_until = index_plot_until(ack_all_timeList_0, plot_until_second)
    # plt.plot(ack_all_timeList_0[:plot_until], ack_all_pList_0[:plot_until], '.', markerfacecolor="#490B04",
    #          markeredgewidth=3,
    #          markersize=10, alpha=1,
    #          markeredgecolor="none", label="{} ACKs".format(label_0))
    #
    # plot_until = index_plot_until(ack_all_timeList_1, plot_until_second)
    # plt.plot(ack_all_timeList_1[:plot_until], ack_all_pList_1[:plot_until], '.', markerfacecolor="#2E347C",
    #          markeredgewidth=3,
    #          markersize=10, alpha=1,
    #          markeredgecolor="none", label="{} ACKs".format(label_1))

    # plot retransmit
    plot_until = index_plot_until(sent_ret_timeList_0, plot_until_second)
    plt.plot(sent_ret_timeList_0[:plot_until], sent_ret_pList_0[:plot_until], 'x', markersize=10, markeredgewidth=5,
             c='#e31a1c',
             label="{} retrans".format(label_0))

    plot_until = index_plot_until(sent_ret_timeList_1, plot_until_second)
    plt.plot(sent_ret_timeList_1[:plot_until], sent_ret_pList_1[:plot_until], 'x', markersize=10, markeredgewidth=5,
             c='#1f78b4',
             label="{} retrans".format(label_1))

    plt.legend(loc="upper right", markerscale=2, fontsize=10)
    # ax2.legend(loc='upper right', markerscale=2, fontsize=20)
    plt.xlabel('time (s)')
    plt.ylabel('sequence number')
    plt.title(plot_title)

    # for ax in [ax1]:
    #     for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
    #                  ax.get_xticklabels() + ax.get_yticklabels()):
    #         item.set_fontsize(20)
    # plt.tight_layout()
    plt.savefig('{}/seq_throughput_over_time--{}.png'.format(plot_carrier_directory, plot_title))
    # plt.close()


def plot_test(pcap_file_0, pcap_file_1, label_0, label_1, plot_until_time):

    if not (pcap_file_0 and pcap_file_1):
        return False

    sent_in_pList_0, sent_in_timeList_0, sent_ret_pList_0, sent_ret_timeList_0, sent_all_pList_0, sent_all_timeList_0, ack_all_pList_0, ack_all_timeList_0, sent_i_count_0, sent_r_count_0, sent_a_count_0, start_timestamp = get_pcap_stat(
        pcap_file_0, server_port="80")

    sent_in_pList_1, sent_in_timeList_1, sent_ret_pList_1, sent_ret_timeList_1, sent_all_pList_1, sent_all_timeList_1, ack_all_pList_1, ack_all_timeList_1, sent_i_count_1, sent_r_count_1, sent_a_count_1, start_timestamp = get_pcap_stat(
        pcap_file_1, server_port="80")

    loss_rate_0 = round(sent_r_count_0 / sent_a_count_0, 5)
    loss_rate_1 = round(sent_r_count_1 / sent_a_count_1, 5)

    plot_title = "{} vs {} --{}--{}".format(label_0, label_1, loss_rate_0, loss_rate_1)

    plot_seq_throughput_over_time(sent_in_timeList_0, sent_in_pList_0, sent_in_timeList_1, sent_in_pList_1,
                       sent_ret_timeList_0, sent_ret_pList_0, sent_ret_timeList_1, sent_ret_pList_1,
                       ack_all_pList_0, ack_all_timeList_0, ack_all_pList_1, ack_all_timeList_1, "./", label_0, label_1, plot_until_time, plot_title=plot_title)

    return True


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
        current_time = (current_ts - initial_ts)/1000
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

    plot_until_time = seconds_buffered[-1][1]
    plt.subplot(2, 1, 1)
    plot_test(pcap0, pcap1, label0, label1, plot_until_time)
    plt.subplot(2, 1, 2)
    plot_bufferedbytes_quality(video_qualities, seconds_buffered, plot_until_time)
    plt.show()


if __name__ == "__main__":
    main()
