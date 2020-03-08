import os
import subprocess
import sys
import json
import statistics


def get_video_stat(video_stat):
    video_stat = json.load(open(video_stat, "r"))

    video_qualities = []
    seconds_buffered = []
    estimated_bandwidths = []
    average_throughputs = []
    initial_ts = video_stat[0]["timestamp"]

    prev_time = video_stat[0]["currentTime"]
    prev_quality = video_stat[0]["quality"]
    buffering_time = 0
    playing_time = 0
    quality_oscillation = 0
    for stat in video_stat:
        quality = stat["quality"]
        if quality != prev_quality:
            quality_oscillation += 1
        prev_quality = quality

        if not stat["buffered"]:
            buffered_until = 0
        else:
            buffered_until = stat["buffered"][0]["end"]
        current_ts = stat["timestamp"]
        current_time = (current_ts - initial_ts) / 1000
        current_playtime = stat["currentTime"]
        buffered = buffered_until - current_playtime
        estimated_bandwidth = stat["bandwidth"]
        if current_playtime - prev_time < 0.4:
            buffering_time += (0.5 - (current_playtime - prev_time))
        else:
            playing_time += (current_playtime - prev_time)
            # only consider buffered seconds if video is actually playing
            seconds_buffered.append(buffered)
            video_qualities.append(quality)

        prev_time = current_playtime
        average_throughput = stat["throughput"]

        estimated_bandwidths.append(estimated_bandwidth)
        average_throughputs.append(average_throughput)
        # video_qualities.append(quality)

    return seconds_buffered, video_qualities, estimated_bandwidths, average_throughputs, quality_oscillation, buffering_time, playing_time


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

    return seq_re, timestamps_re, seq_in, timestamps_in, bytes_in


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


def get_transport_stat(pcap_file):
    seq_re, timestamps_re, seq_in, timestamps_in, bytes_in = get_pcap_seq_all_conns(pcap_file, server_port="80")
    gputs, ts = get_goodput_from_bytes(bytes_in, timestamps_in, 0.5)

    return len(seq_re), len(seq_in), gputs


def get_video_quality_percentage(video_qualities, avg_playing_percentage):
    num_all_qualities = len(video_qualities)
    qualities_dic = {}
    for quality in video_qualities:
        if quality not in qualities_dic:
            qualities_dic[quality] = 0
        qualities_dic[quality] += 1
    quality_percentage = []
    for quality in qualities_dic:
        quality_percentage.append((quality, avg_playing_percentage * qualities_dic[quality]/num_all_qualities))
    quality_percentage.append(("stall", 1 - avg_playing_percentage))

    print(quality_percentage)


def aggregate_stat(raw_stat_dir):
    all_seconds_buffered = []
    all_video_qualities = []
    all_estimated_bandwidths = []
    all_average_throughputs = []
    all_quality_oscillation = []
    all_buffering_time = []
    all_playing_time = []

    num_retrans_client = 0
    num_in_client = 0
    num_retrans_server = 0
    num_in_server = 0
    gputs_client = []
    gputs_server = []
    for file in os.listdir(raw_stat_dir):
        # get avg buffering time / total time
        # get quality percentage during play time
        # get avg estimated throughput
        # get avg buffered time (time to play)
        if ".json" in file:
            seconds_buffered, video_qualities, estimated_bandwidths, average_throughputs, quality_oscillation, buffering_time, playing_time = get_video_stat(
                "{}/{}".format(raw_stat_dir, file))
            all_seconds_buffered += seconds_buffered
            all_video_qualities += video_qualities
            all_estimated_bandwidths += estimated_bandwidths
            all_buffering_time.append(buffering_time)
            all_playing_time.append(playing_time)
            all_quality_oscillation.append(quality_oscillation)
        # get loss rate
        # get throughput
        elif "out.pcap" in file:
            if "client" in file:
                # client side
                num_retrans, num_in, gputs = get_transport_stat("{}/{}".format(raw_stat_dir, file))
                num_retrans_client += num_retrans
                num_in_client += num_in
                gputs_client += gputs
            else:
                # server side
                num_retrans, num_in, gputs = get_transport_stat("{}/{}".format(raw_stat_dir, file))
                num_retrans_server += num_retrans
                num_in_server += num_in
                gputs_server += gputs

    avg_playing_time = statistics.mean(all_playing_time)
    avg_buffering_time = statistics.mean(all_buffering_time)
    avg_buffering_percentage = avg_buffering_time/(avg_buffering_time + avg_playing_time)
    avg_playing_percentage = avg_playing_time/(avg_buffering_time + avg_playing_time)
    print("Application layer:")
    get_video_quality_percentage(all_video_qualities, avg_playing_percentage)
    print("average seconds buffered:", statistics.mean(all_seconds_buffered))
    print("average estimated bandwidth:", statistics.mean(all_estimated_bandwidths))
    print("average buffering percentage:", avg_buffering_percentage)
    print("average playing_time:", avg_playing_percentage)
    print("average quality oscillations", statistics.mean(all_quality_oscillation))

    print("Transport layer:")
    print("average loss rate client:", round(num_retrans_client/(num_retrans_client + num_in_client), 4))
    print("average loss rate server:", round(num_retrans_server / (num_retrans_server + num_in_server), 4))
    print("average goodput client:", statistics.mean(gputs_client))
    print("average goodput server:", statistics.mean(gputs_server))

    return


def main():
    if len(sys.argv) == 2:
        script, raw_stat_dir = sys.argv
    else:
        print("\r\n example run: python3 aggregate_streaming_stat.py raw_stat_dir")
        sys.exit(1)

    aggregate_stat(raw_stat_dir)


if __name__ == "__main__":
    main()
