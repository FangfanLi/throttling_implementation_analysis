import sys
import os
import subprocess
import random
import pickle
import datetime

import numpy as np

from statistics import mean
from statistics import median
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import cross_validate
from sklearn.model_selection import ShuffleSplit
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score
from sklearn.metrics import recall_score

from sklearn.svm import SVC


def read_tests(plots_directory):
    skip_plot_type = "throughput_distribution"
    X = []
    y = []

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
        X.append([avg_server - avg_client, std_client/avg_client, std_server/avg_server, loss_original - loss_inverted])
        y.append(implementation_type)

    return X, y


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

    X, y = read_tests(plots_directory)

    num_folders = 5

    svm = SVC(gamma='auto', probability=True)
    cv = ShuffleSplit(n_splits=num_folders, test_size=0.3, random_state=random.randint(0, 100))
    scores = cross_val_score(svm, X, y, cv=cv)
    print("cross validation scores", scores)

    precisions = []
    recalls = []
    for i in range(num_folders):
        random_state = random.randint(0, 100)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=random_state)
        svm.fit(X_train, y_train)
        y_pred = svm.predict(X_test)
        precision = precision_score(y_test, y_pred, average='micro')
        recall = recall_score(y_test, y_pred, average='micro')
        precisions.append(precision)
        recalls.append(recall)
    print("precisions", precisions)
    print("recalls", recalls)

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


if __name__ == "__main__":
    main()