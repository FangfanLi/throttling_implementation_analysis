import os
import subprocess
import sys
import json
import statistics

QUALITY_TO_BITRATE = {
    "144p": 94963,
    "240p": 217649,
    "360p": 406270,
    "480p": 750192,
    "720p": 1538171,
    "1080p": 2898541,
    "1440p": 8608823,
    "2160p": 2898541
}


def get_video_stat(video_stat):
    video_stat = json.load(open(video_stat, "r"))

    video_qualities = []
    seconds_buffered = []
    estimated_bandwidths = []
    playing_bitrates = []
    initial_ts = video_stat[0]["timestamp"]

    prev_time = video_stat[0]["currentTime"]
    prev_quality = video_stat[0]["quality"]
    joining_time = 0
    buffering_time = 0
    buffering_events = 0
    playing_time = 0
    num_quality_change = 0
    instability_bitrate = 0
    buffering = False
    for stat in video_stat:
        if not stat["buffered"]:
            buffered_until = 0
        else:
            buffered_until = stat["buffered"][0]["end"]
        current_ts = stat["timestamp"]
        current_playtime = stat["currentTime"]
        buffered = buffered_until - current_playtime
        estimated_bandwidth = stat["systemBandwidth"]
        if current_playtime - prev_time < 0.4:
            if not prev_time:
                joining_time = current_ts - initial_ts
            else:
                buffering_time += (0.5 - (current_playtime - prev_time))
                if not buffering:
                    buffering_events += 1
                    buffering = True
        else:
            buffering = False
            quality = stat["quality"]
            current_bitrate = QUALITY_TO_BITRATE[quality]
            playing_bitrates.append(current_bitrate)
            if quality != prev_quality:
                prev_bitrate = QUALITY_TO_BITRATE[prev_quality]
                instability_bitrate += abs(prev_bitrate - current_bitrate)
                num_quality_change += 1
            prev_quality = quality
            playing_time += (current_playtime - prev_time)
            # only consider buffered seconds if video is actually playing
            seconds_buffered.append(buffered)
            video_qualities.append(quality)

        prev_time = current_playtime

        estimated_bandwidths.append(estimated_bandwidth)

    return seconds_buffered, video_qualities, estimated_bandwidths, playing_bitrates, num_quality_change, instability_bitrate, joining_time, buffering_time, playing_time, buffering_events


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
        quality_percentage.append((quality, avg_playing_percentage * qualities_dic[quality] / num_all_qualities))
    quality_percentage.append(("stall", 1 - avg_playing_percentage))

    print(quality_percentage)


def aggregate_stat(raw_stat_dir):
    all_seconds_buffered = []
    all_video_qualities = []
    all_estimated_bandwidths = []
    all_playing_bitrates = []
    all_quality_oscillation = []
    all_instability = []
    all_buffering_time = []
    all_buffering_events = []
    all_playing_time = []
    all_joining_time = []

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
            seconds_buffered, video_qualities, estimated_bandwidths, playing_bitrates, num_quality_change, instability_bitrate, joining_time, buffering_time, playing_time, buffering_events = get_video_stat(
                "{}/{}".format(raw_stat_dir, file))
            all_seconds_buffered += seconds_buffered
            all_video_qualities += video_qualities
            all_estimated_bandwidths += estimated_bandwidths
            all_playing_bitrates += playing_bitrates
            all_buffering_time.append(buffering_time)
            all_buffering_events.append(buffering_events)
            all_joining_time.append(joining_time)
            all_playing_time.append(playing_time)
            all_quality_oscillation.append(num_quality_change)
            instability_score = 0
            if num_quality_change:
                instability_score = instability_bitrate / statistics.mean(playing_bitrates)
            all_instability.append(instability_score)
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
    avg_joining_time = statistics.mean(all_joining_time)
    avg_playing_bitrates = statistics.mean(all_playing_bitrates)
    avg_buffering_percentage = avg_buffering_time / (avg_buffering_time + avg_playing_time)
    avg_buffering_events = statistics.mean(all_buffering_events)
    avg_seconds_buffered = statistics.mean(all_seconds_buffered)
    avg_estimated_bandwidth = statistics.mean(all_estimated_bandwidths)
    avg_quality_oscilations = statistics.mean(all_quality_oscillation)
    avg_instability = statistics.mean(all_instability)
    avg_playing_percentage = avg_playing_time / (avg_buffering_time + avg_playing_time)
    print("Application layer:")
    get_video_quality_percentage(all_video_qualities, avg_playing_percentage)
    print("average seconds buffered:", avg_seconds_buffered)
    print("average estimated bandwidth:", avg_estimated_bandwidth)
    print("average playing bitrates:", avg_playing_bitrates/1E6)
    print("average joining time:", avg_joining_time)
    print("average buffering percentage:", avg_buffering_percentage)
    print("average buffering events:", avg_buffering_events)
    print("average playing_time:", avg_playing_percentage)
    print("average quality oscillations", avg_quality_oscilations)
    print("average instability score", avg_instability)

    avg_loss_rate_client = round(num_retrans_client / (num_retrans_client + num_in_client), 4)
    avg_loss_rate_server = round(num_retrans_server / (num_retrans_server + num_in_server), 4)
    avg_gputs_client = statistics.mean(gputs_client)
    avg_gputs_server = statistics.mean(gputs_server)

    print("Transport layer:")
    print("average loss rate client:", avg_loss_rate_client)
    print("average loss rate server:", avg_loss_rate_server)
    print("average goodput client:", avg_gputs_client)
    print("average goodput server:", avg_gputs_server)

    return avg_joining_time, avg_playing_bitrates, avg_buffering_percentage, avg_buffering_events, avg_seconds_buffered, avg_estimated_bandwidth, avg_quality_oscilations, avg_instability, avg_loss_rate_client, avg_loss_rate_server, avg_gputs_client, avg_gputs_server


def main():
    if len(sys.argv) == 2:
        script, raw_stat_dir = sys.argv
    else:
        print("\r\n example run: python3 aggregate_streaming_stat.py raw_stat_dir")
        sys.exit(1)

    aggregate_stat(raw_stat_dir)


if __name__ == "__main__":
    main()
