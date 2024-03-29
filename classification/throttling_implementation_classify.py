import sys
import os
import subprocess
import random
import pickle
import json
import matplotlib.pyplot as plt

import numpy as np

from statistics import mean
from statistics import median

from sklearn.svm import SVC


def get_implmentation_type(p_val, loss_diff):

    p_val_for_buffer_implementation = 0.001
    p_val_for_policing_implementation = 0.2
    loss_for_policing_implementation = 0.03
    implementation_type = "unknown"

    if (p_val > p_val_for_policing_implementation) and (loss_diff > loss_for_policing_implementation):
        implementation_type = "policing"
    elif (p_val_for_buffer_implementation < p_val < p_val_for_policing_implementation) and (loss_diff < loss_for_policing_implementation):
        implementation_type = "proxy"
    elif (p_val < p_val_for_buffer_implementation) and (loss_diff < loss_for_policing_implementation):
        implementation_type = "buffer"

    return implementation_type


def get_num_correct(plot_dir):
    correct = 0
    wrong = 0
    for plot in os.listdir(plot_dir):
        if "Store" in plot:
            continue

        plot_meta = plot.split("_")
        labeled_type = plot_meta[0]
        p_val = float(plot_meta[4])
        loss_diff = float(plot_meta[6])

        implementation_type = get_implmentation_type(p_val, loss_diff)

        if labeled_type == implementation_type:
            correct += 1
        else:
            print("wrong", labeled_type, implementation_type, p_val, loss_diff)
            wrong += 1

        if labeled_type == "unknown":
            print("unknown", plot)

    return correct, wrong


def partition_tests(plots_directory, num_folders=3):
    skip_plot_type = "throughput_distribution"
    all_tests = []
    for plot in os.listdir(plots_directory):
        if "Store" in plot:
            continue
        plot_info = plot.split(".png")[0]

        # plot_type-client_id-history_count-replayName-avg_client-avg_server-std_client-std_server-loss_original-loss_inverted-implementation_type.png
        plot_meta = plot_info.split("-")
        if len(plot_meta) != 11:
            continue

        plot_type = plot_meta[0]
        client_id = plot_meta[1]
        history_count = plot_meta[2]
        replayName = plot_meta[3]
        avg_client = float(plot_meta[4])
        avg_server = float(plot_meta[5])
        std_client = float(plot_meta[6])
        std_server = float(plot_meta[7])
        loss_original = float(plot_meta[8])
        loss_inverted = float(plot_meta[9])
        implementation_type = float(plot_meta[10])

        if plot_type == skip_plot_type:
            continue

        all_tests.append([avg_client, avg_server, std_client, std_server, loss_original, loss_inverted, implementation_type])

    all_test_set = {}
    all_labels = {}
    # put tests into folders
    for test in all_tests:
        folder_num = random.randint(0, num_folders-1)

        if folder_num not in all_test_set:
            all_test_set[folder_num] = []
            all_labels[folder_num] = []

        all_test_set[folder_num].append(test[:-1])
        all_labels[folder_num].append(test[-1])

    # randomly choose one folder as the test set
    test_set_folder_num = random.randint(0, num_folders - 1)

    test_set = all_test_set[test_set_folder_num]
    test_labels = all_labels[test_set_folder_num]

    training_set = []
    training_labels = []
    for folder_num in all_test_set:
        if folder_num == test_set_folder_num:
            continue
        training_set += all_test_set[folder_num]
        training_labels += all_labels[folder_num]

    return training_set, training_labels, test_set, test_labels


def get_accuracy(svm, test_set, test_labels):
    predict_labels = svm.predict(test_set)
    num_correct = 0
    num_false = 0
    for i in range(len(predict_labels)):
        test_label = test_labels[i]
        predict_label = predict_labels[i]
        if test_label == predict_label:
            num_correct += 1
        else:
            num_false += 1

    return num_correct, num_false


def simple_histogram_plot(data_1, plot_title=""):
    # data_1_90 = data_1[: int(90 * len(data_1) / 100)]
    # interval = max(data_1_90) / float(100)
    interval = 0.01

    bins = []
    for i in range(100):
        bins.append(i * interval)

    fig, ax = plt.subplots(figsize=(15, 6))
    plt.hist(data_1, bins, alpha=0.6, color="#fdbf6f")
    # plt.yscale('log')
    plt.legend(loc='lower right', markerscale=2, fontsize=30)
    # plt.xlabel('Loss percentage')
    plt.xlabel('Percentage of tests with zero loss difference')
    plt.ylabel('Number of samples')
    plt.title(plot_title)

    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
                 ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(20)
    plt.tight_layout()
    plt.savefig('{}/throughput_distribution--{}.png'.format(".", plot_title))
    plt.close()


def simple_histograms_plot(data_1, data_2, plot_title=""):
    data_1_90 = data_1[: int(90 * len(data_1) / 100)]
    data_2_90 = data_2[: int(90 * len(data_2) / 100)]
    interval = max(data_1_90 + data_2_90) / float(100)

    bins = []
    for i in range(100):
        bins.append(i * interval)

    fig, ax = plt.subplots(figsize=(15, 6))
    plt.hist(data_1, bins, alpha=0.3, color="#fdbf6f", label="loss rate original")
    plt.hist(data_2, bins, alpha=0.3, color="#fb9a99", label="loss rate inverted")
    plt.yscale('log')
    plt.legend(loc='lower right', markerscale=2, fontsize=30)
    plt.xlabel('Loss percentage')
    plt.ylabel('Number of samples')
    plt.title(plot_title)

    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
                 ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(20)
    plt.tight_layout()
    plt.savefig('{}/throughput_distribution--{}.png'.format(".", plot_title))
    plt.close()


def calculate_label_percentage(classification_label_percentage, count_tests, count_tests_ISP, count_tests_ISP_replay):
    for label in classification_label_percentage:
        classification_label_percentage[label][1] = classification_label_percentage[label][0]/count_tests
        for ISP in classification_label_percentage[label][2]:
            classification_label_percentage[label][2][ISP][1] = classification_label_percentage[label][2][ISP][0]/count_tests_ISP[ISP]
            for ISP_replay in classification_label_percentage[label][2][ISP][2]:
                classification_label_percentage[label][2][ISP][2][ISP_replay][1] = classification_label_percentage[label][2][ISP][2][ISP_replay][0]/count_tests_ISP_replay[ISP_replay]

    return classification_label_percentage


def main():

    # Use test_stat generated by get_stat_from_wehe_tests.py
    try:
        test_stat = sys.argv[1]
    except:
        print(
            "\r\n Please provide the following input: [test_stat]")
        sys.exit()

    predict_probability_threshold = 0.6
    filename = "trained_model.sav"
    trained_model = pickle.load(open(filename, "rb"))

    wehe_agg_results = json.load(open("weheStat.json", "r"))
    all_throttling_cases = wehe_agg_results["allThrottlingCases"]

    test_stat = json.load(open(test_stat, "r"))

    classification_results_ISP = {}
    classification_results_ISP_replay = {}

    unknown_test_ids = {}
    review_tests = {}
    classification_label_percentage = {}

    count_tests = 0
    count_tests_ISP = {}
    count_tests_ISP_replay = {}

    tests_for_plotting = {}

    for ISP_replay in test_stat:
        ISP_replay_replaced = ISP_replay.replace(")_", ")-")
        if ISP_replay_replaced not in all_throttling_cases.keys():
            continue
        test_stat_ISP_replay = []
        unique_test_ids = []

        ISP = ISP_replay.split(")_")[0]
        replayName = ISP_replay.split(")_")[1]

        for uniqTestID in test_stat[ISP_replay]:
            # [avg_client_tputs_original, avg_server_tputs_original, stdev_client_tputs_original,
            #  stdev_server_tputs_original, loss_rate_original, loss_rate_inverted]
            current_test_stat = test_stat[ISP_replay][uniqTestID]
            avg_client = current_test_stat[0]
            avg_server = current_test_stat[1]
            std_client = current_test_stat[2]
            std_server = current_test_stat[3]
            loss_original = current_test_stat[4]
            loss_inverted = current_test_stat[5]
            # 4 features

            test_stat_ISP_replay.append([(avg_server - avg_client)/avg_client,
                                         (std_server / avg_server) - (std_client / avg_client),
                                         loss_original - loss_inverted, std_client / avg_client])
            # 3 features
            # test_stat_ISP_replay.append([(avg_server - avg_client)/avg_client, (std_server/avg_server) - (std_client/avg_client),
            #                              loss_original - loss_inverted])
            unique_test_ids.append(uniqTestID)

        classification_results = trained_model.predict_proba(test_stat_ISP_replay)

        if ISP_replay not in classification_results_ISP_replay:
            classification_results_ISP_replay[ISP_replay] = {}
        if ISP not in classification_results_ISP:
            classification_results_ISP[ISP] = {}

        # for index in range(len(classification_results)):
        #     classification_label = classification_results[index]
        #
        #     if classification_label not in classification_results_ISP_replay[ISP_replay]:
        #         classification_results_ISP_replay[ISP_replay][classification_label] = 0
        #     if classification_label not in classification_results_ISP[ISP]:
        #         classification_results_ISP[ISP][classification_label] = 0
        #     classification_results_ISP_replay[ISP_replay][classification_label] += 1
        #     classification_results_ISP[ISP][classification_label] += 1

        # prediction with probability
        for index in range(len(classification_results)):
            classification_result = list(classification_results[index])
            uniqTestID = unique_test_ids[index]
            if max(classification_result) < predict_probability_threshold:
                # record the uniqueID of each unknown test, plot them out for further analysis
                classification_label = "unknown"
                if ISP not in unknown_test_ids:
                    unknown_test_ids[ISP] = {}

                if replayName not in unknown_test_ids[ISP]:
                    unknown_test_ids[ISP][replayName] = []
                unknown_test_ids[ISP][replayName].append(uniqTestID)
            else:
                classification_label = classification_result.index(max(classification_result)) + 1

            if classification_label not in classification_results_ISP_replay[ISP_replay]:
                classification_results_ISP_replay[ISP_replay][classification_label] = 0
            if classification_label not in classification_results_ISP[ISP]:
                classification_results_ISP[ISP][classification_label] = 0
            classification_results_ISP_replay[ISP_replay][classification_label] += 1
            classification_results_ISP[ISP][classification_label] += 1

            # if ("ATT (cellular" in ISP) or ("Verizon (cellular" in ISP) or ("TMobile (cellular" in ISP):
            #     if ISP not in tests_for_plotting:
            #         tests_for_plotting[ISP] = {}
            #     if replayName not in tests_for_plotting[ISP]:
            #         tests_for_plotting[ISP][replayName] = {}
            #     if classification_label not in tests_for_plotting[ISP][replayName]:
            #         tests_for_plotting[ISP][replayName][classification_label] = []
            #     if len(tests_for_plotting[ISP][replayName][classification_label]) > 200:
            #         continue
            #     tests_for_plotting[ISP][replayName][classification_label].append(uniqTestID)
            if "Verizon (cellular" in ISP:
                userID = uniqTestID.split("_")[0]

                if userID not in tests_for_plotting:
                    tests_for_plotting[userID] = []
                tests_for_plotting[userID].append(classification_label)

            # count the number of cases of each classification
            # what is the percentage of tests of ISP and ISP-replay that is of this classification
            if classification_label not in classification_label_percentage:
                # [x, y, {}], x is the number of cases, y is the percentage, {} is for individual ISP stat
                classification_label_percentage[classification_label] = [0, 0, {}]
            if ISP not in classification_label_percentage[classification_label][2]:
                classification_label_percentage[classification_label][2][ISP] = [0, 0, {}]
            if ISP_replay not in classification_label_percentage[classification_label][2][ISP][2]:
                classification_label_percentage[classification_label][2][ISP][2][ISP_replay] = [0, 0]

            classification_label_percentage[classification_label][2][ISP][2][ISP_replay][0] += 1
            classification_label_percentage[classification_label][2][ISP][0] += 1
            classification_label_percentage[classification_label][0] += 1

            count_tests += 1
            if ISP not in count_tests_ISP:
                count_tests_ISP[ISP] = 0
            count_tests_ISP[ISP] += 1
            if ISP_replay not in count_tests_ISP_replay:
                count_tests_ISP_replay[ISP_replay] = 0
            count_tests_ISP_replay[ISP_replay] +=1

    # print(classification_label_percentage)
    classification_label_percentage = calculate_label_percentage(classification_label_percentage, count_tests, count_tests_ISP, count_tests_ISP_replay)

    # simple_histogram_plot(zero_loss_difference_rates, plot_title="{}_".format("loss_difference_zero_percentage"))
    json.dump(classification_label_percentage, open("classification_label_percentage.json", "w"))
    json.dump(unknown_test_ids, open("unknown_test_ids.json", "w"))
    json.dump(classification_results_ISP, open("classification_results_ISP.json", "w"))
    json.dump(classification_results_ISP_replay, open("classification_results_ISP_replay.json", "w"))
    json.dump(tests_for_plotting, open("verizon_classification_label_per_user.json", "w"))


if __name__ == "__main__":
    main()