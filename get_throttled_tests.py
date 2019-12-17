'''

Inputs: analysis_result_dir, wehe_record_dir, trace_analysis_dir
Outputs: None, copy throttled tests to trace_analysis_dir

Go through the carriers in the analysis_result_dir directory.
For each carrier,
    check the truePositiveTests files and find these true positive tests,

For each throttled (true positive) test
    find the test in wehe_record_dir
    if it has all files needed
        copy them to the trace_analysis_dir directory

'''

import sys
import os
import json
import glob
import subprocess


def get_true_positive_tests(true_positive_dir, trace_analysis_dir, wehe_record_dir, num_true_positive=100):
    true_positive_per_carrier = []
    for true_positive_file in os.listdir(true_positive_dir):
        cnt_true_positive_per_carrier_replay = 0
        true_positive_file = true_positive_dir + "/" + true_positive_file
        true_positive_per_replay = json.load(open(true_positive_file, "r"))
        for true_positive_test in true_positive_per_replay:
            # check whether the necessary files exist
            original_pcap_file, inverted_pcap_file, regex_replayInfo_file, regex_xput_original_file, regex_xput_inverted_file, regex_mobileStat_file = get_test_files(
                true_positive_test["uniqueTestID"], trace_analysis_dir, wehe_record_dir)
            if not (original_pcap_file and inverted_pcap_file and regex_replayInfo_file and regex_xput_original_file and regex_xput_inverted_file and regex_mobileStat_file):
                continue
            true_positive_per_carrier.append(true_positive_test["uniqueTestID"])
            cnt_true_positive_per_carrier_replay += 1
            if cnt_true_positive_per_carrier_replay > num_true_positive:
                break

    return true_positive_per_carrier


def get_tcpdump_file(tcpdumpsResults_dir, userID, historyCount):
    regex_original_pcap = "*_{}_*_{}_{}*".format(userID, historyCount, 0)
    regex_inverted_pcap = "*_{}_*_{}_{}*".format(userID, historyCount, 1)

    original_pcap_file = glob.glob(tcpdumpsResults_dir + regex_original_pcap)
    inverted_pcap_file = glob.glob(tcpdumpsResults_dir + regex_inverted_pcap)

    if not (original_pcap_file and inverted_pcap_file):
        return None, None
    else:
        original_pcap_file = original_pcap_file[0]
        inverted_pcap_file = inverted_pcap_file[0]
        return original_pcap_file, inverted_pcap_file


def get_file_from_partial_name(file_partial_name):
    file_name = glob.glob(file_partial_name)
    if file_name:
        return file_name[0]
    else:
        return None


def get_test_files(positive_test_id, trace_analysis_dir, wehe_record_dir):
    userID = positive_test_id.split("_")[0]
    historyCount = positive_test_id.split("_")[1]
    user_dir = wehe_record_dir + "/" + userID + "/"
    replayInfo_dir = user_dir + "/replayInfo/"
    mobileStat_dir = user_dir + "/mobileStats/"
    tcpdumpsResults_dir = user_dir + "/tcpdumpsResults/"
    clientXputs_dir = user_dir + "/clientXputs/"

    original_pcap_file, inverted_pcap_file = get_tcpdump_file(tcpdumpsResults_dir, userID, historyCount)

    user_trace_dir = trace_analysis_dir + "/" + userID
    user_trace_replay_dir = user_trace_dir + "/replayInfo/"
    user_trace_mobileStat_dir = user_trace_dir + "/mobileStats/"
    user_trace_tcpdump_dir = user_trace_dir + "/tcpdumpsResults/"
    user_trace_clientXputs_dir = user_trace_dir + "/clientXputs/"

    if not os.path.isdir(user_trace_dir):
        os.mkdir(user_trace_dir)
        os.mkdir(user_trace_replay_dir)
        os.mkdir(user_trace_mobileStat_dir)
        os.mkdir(user_trace_tcpdump_dir)
        os.mkdir(user_trace_clientXputs_dir)

    regex_replayInfo_file = "{}/replayInfo_{}_{}_0.json".format(replayInfo_dir, userID, historyCount)
    regex_xput_original_file = "{}/Xput_{}_{}_0.json".format(clientXputs_dir, userID, historyCount)
    regex_xput_inverted_file = "{}/Xput_{}_{}_1.json".format(clientXputs_dir, userID, historyCount)
    regex_mobileStat_file = "{}/mobileStats_{}_{}_0.json".format(mobileStat_dir, userID, historyCount)

    regex_replayInfo_file = get_file_from_partial_name(regex_replayInfo_file)
    regex_xput_original_file = get_file_from_partial_name(regex_xput_original_file)
    regex_xput_inverted_file = get_file_from_partial_name(regex_xput_inverted_file)
    regex_mobileStat_file = get_file_from_partial_name(regex_mobileStat_file)

    return original_pcap_file, inverted_pcap_file, regex_replayInfo_file, regex_xput_original_file, regex_xput_inverted_file, regex_mobileStat_file


def copy_test_files(true_positive_ids_per_carrier, trace_analysis_dir, wehe_record_dir):
    for positive_test_id in true_positive_ids_per_carrier:
        userID = positive_test_id.split("_")[0]
        historyCount = positive_test_id.split("_")[1]
        user_dir = wehe_record_dir + "/" + userID + "/"
        replayInfo_dir = user_dir + "/replayInfo/"
        mobileStat_dir = user_dir + "/mobileStats/"
        tcpdumpsResults_dir = user_dir + "/tcpdumpsResults/"
        clientXputs_dir = user_dir + "/clientXputs/"

        original_pcap_file, inverted_pcap_file = get_tcpdump_file(tcpdumpsResults_dir, userID, historyCount)

        if not original_pcap_file:
            continue

        user_trace_dir = trace_analysis_dir + "/" + userID
        user_trace_replay_dir = user_trace_dir + "/replayInfo/"
        user_trace_mobileStat_dir = user_trace_dir + "/mobileStats/"
        user_trace_tcpdump_dir = user_trace_dir + "/tcpdumpsResults/"
        user_trace_clientXputs_dir = user_trace_dir + "/clientXputs/"

        if not os.path.isdir(user_trace_dir):
            os.mkdir(user_trace_dir)
            os.mkdir(user_trace_replay_dir)
            os.mkdir(user_trace_mobileStat_dir)
            os.mkdir(user_trace_tcpdump_dir)
            os.mkdir(user_trace_clientXputs_dir)

        regex_replayInfo_file = "{}/replayInfo_{}_{}_0.json".format(replayInfo_dir, userID, historyCount)
        regex_xput_original_file = "{}/Xput_{}_{}_0.json".format(clientXputs_dir, userID, historyCount)
        regex_xput_inverted_file = "{}/Xput_{}_{}_1.json".format(clientXputs_dir, userID, historyCount)
        regex_mobileStat_file = "{}/mobileStats_{}_{}_0.json".format(mobileStat_dir, userID, historyCount)

        cmd_cp_replayInfo = ["cp", regex_replayInfo_file, user_trace_replay_dir]
        cmd_cp_mobileStat = ["cp", regex_mobileStat_file, user_trace_mobileStat_dir]
        cmd_cp_xput = ["cp", regex_xput_original_file, regex_xput_inverted_file, user_trace_clientXputs_dir]
        cmd_cp_tcpdump = ["cp", original_pcap_file, inverted_pcap_file, user_trace_tcpdump_dir]

        proc = subprocess.run(cmd_cp_replayInfo)
        proc = subprocess.run(cmd_cp_xput)
        proc = subprocess.run(cmd_cp_tcpdump)

        if os.path.isfile(regex_mobileStat_file):
            proc = subprocess.run(cmd_cp_mobileStat)


def main():
    try:
        analysis_result_dir = sys.argv[1]
        wehe_record_dir = sys.argv[2]
        trace_analysis_dir = sys.argv[3]
        num_true_positive = int(sys.argv[4])
    except:
        print(
            '\r\n Please provide the following four inputs: [analysis_result_dir] [wehe_record_dir] [trace_analysis_dir] [num_true_positive_per_carrier_replay]')
        sys.exit()

    if not os.path.isdir(trace_analysis_dir):
        os.mkdir(trace_analysis_dir)

    all_true_positive_ids = []

    for carrier in os.listdir(analysis_result_dir):
        carrier_dir = analysis_result_dir + "/" + carrier
        true_positive_dir = carrier_dir + "/truePositiveTests"

        if not os.path.exists(true_positive_dir):
            print("not true positive", true_positive_dir)
            continue

        all_true_positive_ids += get_true_positive_tests(true_positive_dir, trace_analysis_dir, wehe_record_dir,
                                                         num_true_positive)

    copy_test_files(all_true_positive_ids, trace_analysis_dir, wehe_record_dir)


if __name__ == "__main__":
    main()