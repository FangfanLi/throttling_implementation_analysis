import sys
import os
import subprocess
import random
import pickle
import datetime

import numpy as np

from statistics import mean
from statistics import median
from sklearn.metrics import precision_recall_fscore_support

from sklearn.svm import SVC


def partition_tests(plots_directory, num_folders=3):
    skip_plot_type = "throughput_distribution"
    all_tests = []

    for plot in os.listdir(plots_directory):
        if "png" not in plot:
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


def main():

    # Use plots in plots_directory to form a list of data
    # each plot has
    # 1. the avg for both client and server side throughput
    # 2. the stdev for both client and server side throughput
    # 3. loss rate for original replay and bit-inverted replay
    try:
        plots_directory = sys.argv[1]
    except:
        print(
            '\r\n Please provide the following input: [plots_directory] <num_folders>')
        sys.exit()

    num_folders = 5
    if len(sys.argv) == 3:
        num_folders = int(sys.argv[2])

    training_set, training_labels, test_set, test_labels = partition_tests(plots_directory, num_folders)

    X = np.array(training_set)
    y = np.array(training_labels)

    svm = SVC(gamma='auto')
    svm.fit(X, y)
    today_date = datetime.datetime.today()
    today_date = today_date.strftime("%d-%B-%Y")

    model_dir = "./models/"

    if not os.path.exists(model_dir):
        os.mkdir(model_dir)

    filename = "svm_model.sav"
    timestamped_filename = "{}svm_model_{}.sav".format(model_dir, today_date)
    pickle.dump(svm, open(filename, 'wb'))
    pickle.dump(svm, open(timestamped_filename, 'wb'))

    predict_labels = svm.predict(test_set)
    precision, recall, fbeta_score, support = precision_recall_fscore_support(test_labels,predict_labels, average='weighted')
    print("precision {}, recall {}, fbeta {}, support {}".format(precision, recall, fbeta_score, support))

if __name__ == "__main__":
    main()