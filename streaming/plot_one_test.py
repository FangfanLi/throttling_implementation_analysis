'''
This script plots Wehe tests
# For the original replay (observed by the client and the server)
1. What are the average throughput?
2. What are the standard deviations in throughput samples.

# For the server side stat (original and bit-inverted)
1. What are the loss rates?

Input : the directory containing all tests, output graphs
    For each test:
        Find the tcpdump and client side throughput samples for both original and bit-inverted replays
        Computes:
          1. Average throughput for client-original and server-original
          2. Standard deviation for client-original and server-original
          3. Loss rates for server-original and server-inverted
        Outputs
          1. Graph including computed stats in the name:
             client_id-history_count-replayName-avg_client-avg_server-std_client-std_server-loss_original-loss_inverted.jpg) :
             a. The sequence over time graph (seqs sent from the server, acks received on the server, seqs reconstructed on the client)
             b. Throughput sample distribution/histogram

For sequence over time graph:
Red dots for the original replay, small darker red dots for acks, Xs for retransmission, orange dots for client side data
Blue dots for the bit-inverted replay, small darker blue dots for acks, Xs for retransmission, blue dots for client side data

For throughput samples graph
Red line for the original replays, dashed line for client side throughput samples
Blue line for the bit-inverted replays, dashed line for client side throughput samples
'''

import sys
import subprocess
import os
import glob
import json
import pickle
import statistics

import matplotlib.pyplot as plt
from sklearn.metrics import r2_score

APPNAME_TO_PORT = {
    "Vimeo": "443",
    "Spotify": "80",
    "NBCSports": "80",
    "Youtube": "443",
    "Amazon (HTTPS)": "443",
    # doesn't really matter as Skype is UDP
    "Skype": "443",
    "Netflix": "443",
    "Amazon (HTTP)": "80",
    "Vimeo (vimeocdn)": "80",
    "FacebookVideo": "443",
    "Hulu": "443",
    # doesn't really matter as WhatsApp is UDP
    "WhatsApp": "443",
    "Twitch": "443",
    "AppleMusic": "80"
}

try:
    import seaborn as sns

    sns.set()
except ImportError:
    pass


def list2CDF(myList):
    myList = sorted(myList)

    x = [0]
    y = [0]

    for i in range(len(myList)):
        x.append(myList[i])
        y.append(float(i + 1) / len(myList))

    return x, y


def doXputs(pcapFile):
    # Run tshark
    # Use fixed number of buckets

    dcmd = ['tshark', '-r', pcapFile, '-T', 'fields', '-e', 'frame.time_relative']
    dp = subprocess.Popen(dcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    doutput, derr = dp.communicate()
    # tshark -r <filename> -R "tcp.stream eq <index>" -T fields -e frame.time_epoch
    duration = doutput.splitlines()[-1]
    # Dynamic xputInterval = (replay duration / # buckets)
    xputInterval = float(duration) / 100

    cmd = ['tshark', '-r', pcapFile, '-qz', 'io,stat,' + str(xputInterval)]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = p.communicate()

    # Parse tshark output
    lines = output.splitlines()
    end = lines[4].partition('Duration:')[2].partition('secs')[0].replace(' ', '')
    lines[-2] = lines[-2].replace('Dur', end)

    ts = []
    xput = []

    for l in lines:
        if '<>' not in l:
            continue

        l = l.replace('|', '')
        l = l.replace('<>', '')
        parsed = map(float, l.split())

        start = float(parsed[0])
        end = float(parsed[1])
        dur = end - start

        # if dur == 0 or ((float(parsed[-1])/dur)*8/1000000.0 > 23):
        if dur == 0:
            continue

        ts.append(end)
        xput.append(float(parsed[-1]) / dur)

    xput = map(lambda x: x * 8 / 1000000.0, xput)

    return ts[:-1], xput[:-1]


def doXputsCDFplots(gputs_original, client_gputs_original, gputs_inverted,
                    client_gputs_inverted, directory=".", title=""):
    color_original = "#99000d"
    color_inverted = "#034e7b"

    gputs_original = [x for x in gputs_original if x >= 0]
    client_xputs_original = [x for x in client_gputs_original if x >= 0]

    gputs_inverted = [x for x in gputs_inverted if x >= 0]
    client_xputs_inverted = [x for x in client_gputs_inverted if x >= 0]

    fig, ax = plt.subplots(figsize=(12, 8))
    gputs_original_x, gputs_original_y = list2CDF(gputs_original)
    client_xputs_original_x, client_xputs_original_y = list2CDF(client_xputs_original)

    gputs_inverted_x, gputs_inverted_y = list2CDF(gputs_inverted)
    client_xputs_inverted_x, client_xputs_inverted_y = list2CDF(client_xputs_inverted)

    # plot original throughput CDF
    plt.plot(gputs_original_x, gputs_original_y, color=color_original, linewidth=2,
             label='Original goodput server')
    plt.plot(client_xputs_original_x, client_xputs_original_y, '-.', color=color_original, linewidth=2,
             label='Original goodput client')

    # plot bit-inverted throughput CDF
    plt.plot(gputs_inverted_x, gputs_inverted_y, color=color_inverted, linewidth=2,
             label='Bit inverted goodput server')
    plt.plot(client_xputs_inverted_x, client_xputs_inverted_y, '-.', color=color_inverted, linewidth=2,
             label='Bit inverted goodput client')

    plt.legend(loc='lower right', fontsize=20)
    plt.grid()
    plt.xlabel('Xput (Mbits/sec)')
    plt.ylabel('CDF')
    plt.ylim((0, 1.1))

    if title:
        plt.title(title)

    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
                 ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(20)

    plt.tight_layout()
    plt.savefig("{}/{}_gputCDF.png".format(directory, title))
    plt.close()


def doTputsInterval(timeL, packetL, client_sampling_interval):
    initS = packetL[0]

    sequence = [(int(x) - int(initS)) for x in packetL]
    timeL = [float(x) for x in timeL]

    duration = timeL[-1]
    xput_interval = client_sampling_interval

    # print("duration, interval", duration, xput_interval)

    untilT = xput_interval
    lastT = 0
    tputs = []
    ts = []
    for i in range(len(timeL)):
        # Calculate bytes sent during this period
        if timeL[i] >= untilT:
            tputs.append((sequence[i] - sequence[lastT]) / xput_interval)
            lastT = i
            untilT += xput_interval
            ts.append(timeL[i])

    tputs = [x * 8 / 1000000.0 for x in tputs]

    return tputs, ts


def doTputs(timeL, packetL, num_buckets=None):
    initS = packetL[0]

    sequence = [(int(x) - int(initS)) for x in packetL]
    timeL = [float(x) for x in timeL]

    if not num_buckets:
        # If number of bucket is not specified, use 100 buckets
        num_buckets = 100
    else:
        num_buckets = num_buckets

    duration = timeL[-1]
    xput_interval = float(duration) / num_buckets

    # print("duration, interval", duration, xput_interval)

    untilT = xput_interval
    lastT = 0
    tputs = []
    ts = []
    for i in range(len(timeL)):
        # Calculate bytes sent during this period
        if timeL[i] >= untilT:
            tputs.append((sequence[i] - sequence[lastT]) / xput_interval)
            lastT = i
            untilT += xput_interval
            ts.append(timeL[i])

    tputs = [x * 8 / 1000000.0 for x in tputs]

    return tputs, ts


def get_client_pcap_stat(pcapFile, server_port=None):
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

    # All Packets arrived on the client
    arr_all_pList = []
    arr_all_timeList = []

    # Packets arrived on the client in order
    arr_in_pList = []
    arr_in_timeList = []
    # Packets arrived on the client, re transmission
    arr_ret_pList = []
    arr_ret_timeList = []
    # Packets arrived on the client, out-of-order transmission
    arr_out_pList = []
    arr_out_timeList = []

    # All Packets sent from the client
    sent_all_pList = []
    sent_all_timeList = []

    # Packets sent *from* client, in order
    sent_in_pList = []
    sent_in_timeList = []
    # Packets sent *from* client, re transmission
    sent_ret_pList = []
    sent_ret_timeList = []
    # Packets sent *from* client, out-of-order transmission
    sent_out_pList = []
    sent_out_timeList = []

    for sl in output.splitlines():
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

        # For packets sent from the server, put in the arr_* lists
        if src_port == server_port:
            arr_all_pList.append(seq)
            arr_all_timeList.append(time)
            if ret:
                arr_ret_pList.append(seq)
                arr_ret_timeList.append(time)
            elif out:
                arr_out_pList.append(seq)
                arr_out_timeList.append(time)
            else:
                arr_in_pList.append(seq)
                arr_in_timeList.append(time)
        # For packets sent from on the client, put in the send_* lists
        else:
            sent_all_pList.append(ack)
            sent_all_timeList.append(time)
            if ret:
                sent_ret_pList.append(ack)
                sent_ret_timeList.append(time)
            elif out:
                sent_out_pList.append(ack)
                sent_out_timeList.append(time)
            else:
                sent_in_pList.append(ack)
                sent_in_timeList.append(time)

    start_timestamp = 0
    start_seq = 0

    arr_all_pList = [float(x) - start_seq for x in arr_all_pList]
    arr_all_timeList = [float(x) - start_seq for x in arr_all_timeList]
    arr_in_pList = [float(x) - start_seq for x in arr_in_pList]
    arr_ret_pList = [float(x) - start_seq for x in arr_ret_pList]
    arr_in_timeList = [float(x) - start_timestamp for x in arr_in_timeList]
    arr_ret_timeList = [float(x) - start_timestamp for x in arr_ret_timeList]

    return arr_all_pList, arr_all_timeList, arr_in_pList, arr_in_timeList, arr_ret_pList, arr_ret_timeList, start_timestamp


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


def timestamp_after_start(timestamps, start_timestamp):
    cnt = 0
    for timestamp in timestamps:
        if float(timestamp) > start_timestamp:
            break
        cnt += 1
    return cnt


# data directory should have subdirectories:
# 1. clientXputs
# 2. tcpdumpsResults
def load_replay_files(data_directory, history_count, testID):
    clientXputs_dir = data_directory + "/clientXputs/"
    tcpdumpsResults_dir = data_directory + "/tcpdumpsResults/"
    client_tcpdumps_dir = data_directory + "/client_tcpdump/"
    regex_pcap = "*_{}_{}*".format(history_count, testID)

    server_pcap_file = glob.glob(tcpdumpsResults_dir + regex_pcap)
    client_pcap_file = glob.glob(client_tcpdumps_dir + regex_pcap)

    if not server_pcap_file:
        return None, [], [], []
    else:
        server_pcap_file = server_pcap_file[0]

    if not client_pcap_file:
        return None, [], [], []
    else:
        client_pcap_file = client_pcap_file[0]

    original_clientXputs_json = clientXputs_dir + "Xput_*_{}_{}.json".format(history_count, testID)
    original_clientXputs_json = glob.glob(original_clientXputs_json)[0]

    try:
        xputO = tsO = []
        if os.path.exists(original_clientXputs_json):
            (xputO, tsO) = json.load(open(original_clientXputs_json, 'r'))

    except Exception as e:
        print("FAIL at loading client side throughputs", e)
        xputO = tsO = []

    return server_pcap_file, client_pcap_file, xputO, tsO


def bytes_over_time_from_throughput(client_tputs, client_ts, start_timestamp=None):
    received_bytes = []
    received_ts = []

    sampling_interval = client_ts[1] - client_ts[0]
    current_bytes = 0

    for i in range(len(client_tputs)):
        if client_ts[i] < start_timestamp:
            continue
        current_bytes += client_tputs[i] * sampling_interval * 1E6 / 8
        received_bytes.append(current_bytes)
        received_ts.append(client_ts[i] - start_timestamp)

    return received_ts, received_bytes


def get_r_squared_score(seqs, time_stamps, throttling_rate, plot_title='test'):
    seqs = [int(x) for x in seqs]
    time_stamps = [float(x) for x in time_stamps]
    throttling_line = [int(float(x) * throttling_rate * 1E6 / 8) for x in time_stamps]

    fig, ax = plt.subplots(figsize=(20, 8))

    if 'server' in plot_title:
        marker_label = "Server sent"
    else:
        marker_label = "Client received"

    plt.plot(time_stamps, seqs, 'o',
             markeredgecolor='#fb9a99', markerfacecolor='none', markeredgewidth=3, label=marker_label)

    plt.plot(time_stamps, throttling_line, linewidth=5,
             color='#a6cee3', label='Throttling line {} Mbps'.format(throttling_rate))

    plt.legend(loc='lower right', markerscale=2, fontsize=30)
    plt.xlabel('time (s)')
    plt.ylabel('sequence number')
    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
                 ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(20)
    plt.tight_layout()
    plt.title("r2 score {}".format(round(r2_score(seqs, throttling_line), 2)))

    plt.savefig('{}.png'.format(plot_title))
    plt.close()


def plot_seq_over_time(sent_in_timeList_original, sent_in_pList_original, sent_in_timeList_inverted,
                       sent_in_pList_inverted,
                       receive_timeList_original, receive_pList_original, receive_timeList_inverted,
                       receive_pList_inverted,
                       sent_ret_timeList_original, sent_ret_pList_original, sent_ret_timeList_inverted,
                       sent_ret_pList_inverted,
                       plot_carrier_directory, plot_title=""):
    fig, ax = plt.subplots(figsize=(20, 8))

    # plot sequence for original replay
    plt.plot(sent_in_timeList_original, sent_in_pList_original, 'o', markerfacecolor="#fb9a99",
             markeredgewidth=3,
             markersize=15, alpha=0.1,
             markeredgecolor="none", label='Original first trans')

    # plot sequence for inverted replay
    plt.plot(sent_in_timeList_inverted, sent_in_pList_inverted, 'o', markerfacecolor="#a6cee3",
             markeredgewidth=3,
             markersize=15, alpha=0.1,
             markeredgecolor="none", label='Inverted first trans')

    # plot bytes received on client
    plt.plot(receive_timeList_original, receive_pList_original, 'o', markerfacecolor="#fdbf6f",
             markeredgewidth=3,
             markersize=15, alpha=0.1,
             markeredgecolor="none", label='Original received on client')

    plt.plot(receive_timeList_inverted, receive_pList_inverted, 'o', markerfacecolor="#b2df8a",
             markeredgewidth=3,
             markersize=15, alpha=0.1,
             markeredgecolor="none", label='Inverted received on client')

    # plot retransmit
    plt.plot(sent_ret_timeList_original, sent_ret_pList_original, 'x', markersize=18, markeredgewidth=5,
             c='#e31a1c',
             label='Original retrans')

    plt.plot(sent_ret_timeList_inverted, sent_ret_pList_inverted, 'x', markersize=18, markeredgewidth=5,
             c='#1f78b4',
             label='Inverted retrans')

    plt.legend(loc='lower right', markerscale=2, fontsize=30)
    plt.xlabel('time (s)')
    plt.ylabel('sequence number')
    plt.title(plot_title)

    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
                 ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(20)
    # plt.tight_layout()
    plt.savefig('{}/seq_over_time--{}.png'.format(plot_carrier_directory, plot_title))
    plt.close()


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


def plot_seq_throughput_over_time(sent_in_timeList_original, sent_in_pList_original, arr_client_in_timeList,
                                  arr_client_in_pList,
                                  sent_ret_timeList_original, sent_ret_pList_original, arr_client_ret_timeList,
                                  arr_client_ret_pList,
                                  server_tputs_original, server_ts_original, client_tputs_original, client_ts_original,
                                  plot_carrier_directory, plot_title=""):
    fig, ax1 = plt.subplots(figsize=(20, 8))

    plot_until_second = 200
    ax2 = ax1.twinx()

    ax2.set_ylabel('throughput (Mbps)')

    plot_until = index_plot_until(server_ts_original, plot_until_second)
    ax2.plot(server_ts_original[:plot_until], server_tputs_original[:plot_until], color="#fb9a99", linewidth=2,
             label='Sent from server')
    plot_until = index_plot_until(client_ts_original, plot_until_second)
    ax2.plot(client_ts_original[:plot_until], client_tputs_original[:plot_until], color="#fdbf6f", linewidth=2,
             label='Received on client')

    # plot sequence for original replay
    plot_until = index_plot_until(sent_in_timeList_original, plot_until_second)
    ax1.plot(sent_in_timeList_original[:plot_until], sent_in_pList_original[:plot_until], 'o',
             markerfacecolor="#fb9a99",
             markeredgewidth=3,
             markersize=15, alpha=0.1,
             markeredgecolor="none", label='Server first trans')

    # plot sequence for inverted replay
    plot_until = index_plot_until(arr_client_in_timeList, plot_until_second)
    ax1.plot(arr_client_in_timeList[:plot_until], arr_client_in_pList[:plot_until], 'o',
             markerfacecolor="#fdbf6f",
             markeredgewidth=3,
             markersize=15, alpha=0.1,
             markeredgecolor="none", label='Client first trans')

    # plot retransmit
    plot_until = index_plot_until(sent_ret_timeList_original, plot_until_second)
    ax1.plot(sent_ret_timeList_original[:plot_until], sent_ret_pList_original[:plot_until], 'x', markersize=18,
             markeredgewidth=5,
             c='#e31a1c',
             label='Server retrans')

    plot_until = index_plot_until(arr_client_ret_timeList, plot_until_second)
    ax1.plot(arr_client_ret_timeList[:plot_until], arr_client_ret_pList[:plot_until], 'x', markersize=18,
             markeredgewidth=5,
             c='#996600',
             label='Client retrans')

    ax1.legend(loc="upper right", bbox_to_anchor=(2,2), markerscale=2, fontsize=20)
    ax2.legend(loc='upper right', markerscale=2, fontsize=20)
    plt.xlabel('time (s)')
    ax1.set_ylabel('sequence number')
    plt.title(plot_title)

    for ax in [ax1, ax2]:
        for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
                     ax.get_xticklabels() + ax.get_yticklabels()):
            item.set_fontsize(20)
    # plt.tight_layout()
    plt.savefig('{}/seq_throughput_over_time--{}.png'.format(plot_carrier_directory, plot_title))
    plt.close()


def plot_test(data_directory, plot_historyCount, result_directory, server_port):
    if not os.path.isdir(result_directory):
        os.mkdir(result_directory)

    # get pcap_file and client side throughput samples
    original_server_pcap_file, original_client_pcap_file, client_tputs_original, client_ts_original = load_replay_files(
        data_directory, plot_historyCount, "0")
    # inverted_server_pcap_file, inverted_client_pcap_file, client_tputs_inverted, client_ts_inverted = load_replay_files(
    #     data_directory, plot_historyCount, "1")

    if not (
            original_server_pcap_file and original_client_pcap_file and client_ts_original):
        return False

    sent_in_pList_original, sent_in_timeList_original, sent_ret_pList_original, sent_ret_timeList_original, sent_all_pList_original, sent_all_timeList_original, ack_all_pList_original, ack_all_timeList_original, sent_i_count_original, sent_r_count_original, sent_a_count_original, start_timestamp = get_pcap_stat(
        original_server_pcap_file, server_port=server_port)

    arr_client_all_pList, arr_client_all_timeList, arr_client_in_pList, arr_client_in_timeList, arr_client_ret_pList, arr_client_ret_timeList, start_timestamp = get_client_pcap_stat(
        original_client_pcap_file, server_port=server_port)

    receive_timeList_original, receive_pList_original = bytes_over_time_from_throughput(client_tputs_original,
                                                                                        client_ts_original,
                                                                                        start_timestamp)

    if not (sent_in_pList_original and arr_client_in_pList and receive_pList_original and ack_all_pList_original):
        return False

    client_sampling_interval = client_ts_original[1] - client_ts_original[0]
    server_tputs_original, server_ts_original = doTputsInterval(sent_in_timeList_original, sent_in_pList_original,
                                                                client_sampling_interval)

    client_tputs_original, client_ts_original = doTputsInterval(arr_client_in_timeList, arr_client_in_pList,
                                                                client_sampling_interval)

    if (len(client_tputs_original) < 10) or (len(server_tputs_original) < 10):
        return False

    avg_client_tputs_original = round(statistics.mean(client_tputs_original), 5)
    avg_server_tputs_original = round(statistics.mean(server_tputs_original), 5)
    stdev_client_tputs_original = round(statistics.stdev(client_tputs_original), 5)
    stdev_server_tputs_original = round(statistics.stdev(server_tputs_original), 5)

    loss_rate_original = round(sent_r_count_original / sent_a_count_original, 5)
    loss_rate_client_original = round(len(arr_client_ret_pList) / len(arr_client_all_pList), 5)

    plot_title = "{}--{}--{}--{}--{}--{}--{}".format(plot_historyCount,
                                                     avg_client_tputs_original,
                                                     avg_server_tputs_original, stdev_client_tputs_original,
                                                     stdev_server_tputs_original, loss_rate_original,
                                                     loss_rate_client_original)

    plot_seq_throughput_over_time(sent_in_timeList_original, sent_in_pList_original, arr_client_in_timeList,
                                  arr_client_in_pList,
                                  sent_ret_timeList_original, sent_ret_pList_original, arr_client_ret_timeList,
                                  arr_client_ret_pList,
                                  server_tputs_original, server_ts_original, client_tputs_original, client_ts_original,
                                  result_directory, plot_title=plot_title)

    plot_throughput_distribution(client_tputs_original, server_tputs_original, result_directory,
                                 plot_title=plot_title)

    return True


def get_test_metadata(client_dir, replayInfo):
    # get test metaInfo (in the file name)
    meta_info = replayInfo.split('.')[0].split('_')
    # there should be 5 different info in the file name
    if len(meta_info) != 4:
        return None, None
    userID = meta_info[1]
    historyCount = meta_info[2]
    testID = meta_info[3]

    # ignore the DPI tests for now
    if testID not in ['0', '1']:
        return None, None

    mobileStatsFileName = 'mobileStats_{}_{}_{}'.format(userID, historyCount, testID)

    replayInfoFileName = client_dir + '/replayInfo/' + replayInfo
    mobileStatsFile = client_dir + '/mobileStats/' + mobileStatsFileName

    try:
        replayInfo = json.load(open(replayInfoFileName, 'r'))
    except:
        return None, None

    if not replayInfo:
        return None, None

    return replayInfo, mobileStatsFile


def plot_one_test(data_directory, result_directory, plot_historyCount, server_port):
    tcpdumpResults_dir = data_directory + '/tcpdumpsResults/'
    if not os.path.isdir(tcpdumpResults_dir):
        return False

    test_stat = plot_test(data_directory, plot_historyCount, result_directory, server_port)

    return True


def main():
    try:
        data_directory = sys.argv[1]
        plot_directory = sys.argv[2]
        historyCount = int(sys.argv[3])
        server_port = sys.argv[4]
    except:
        print(
            '\r\n Please provide the following four inputs: [data_directory] [plot_directory] [historyCount] [server_port]')
        sys.exit()

    plot_one_test(data_directory, plot_directory, historyCount, server_port)


if __name__ == "__main__":
    main()
