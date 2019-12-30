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
from sklearn.model_selection import KFold
from sklearn.metrics import precision_score
from sklearn.metrics import recall_score

from sklearn.linear_model import LogisticRegression

from sklearn.svm import SVC

train_stat_to_test = {}

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
        X.append([avg_server - avg_client, (std_server/avg_server) - (std_client/avg_client), loss_original - loss_inverted])
        # X.append([avg_server - avg_client, std_client/avg_client, std_server/avg_server, loss_original - loss_inverted])
        y.append(implementation_type)

        # train_stat_to_test[(avg_server - avg_client, std_client/avg_client, std_server/avg_server, loss_original - loss_inverted)] = "{}_{}".format(client_id, history_count)
        train_stat_to_test[(avg_server - avg_client, (std_server/avg_server) - (std_client/avg_client), loss_original - loss_inverted)] = "{}_{}".format(client_id, history_count)

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

    trained_model = SVC(gamma='auto', probability=True)
    probability_threshold = 0.5

    score_all = []
    # random_state = random.randint(0, 100)

    kf = KFold(n_splits=5, random_state=None, shuffle=False)
    X = np.array(X)
    y = np.array(y)
    iter_count = 0

    for train_index, test_index in kf.split(X):
        print("count iteration ", iter_count)
        X_train, X_test = X[train_index], X[test_index]
        y_train, y_test = y[train_index], y[test_index]
        count_unknown = 0
        count_wrong = 0
        count_correct = 0
        trained_model.fit(X_train, y_train)
        X_test = list(X_test)
        y_pred = trained_model.predict_proba(X_test)
        for index in range(len(y_pred)):
            # X_test_data = list(X_test[index])
            y_pred_proba = list(y_pred[index])
            if max(y_pred_proba) < probability_threshold:
                count_unknown += 1
                # print("unknown, pred, test", (X_test_data[0], X_test_data[1], X_test_data[2]), train_stat_to_test[(X_test_data[0], X_test_data[1], X_test_data[2])], y_pred_proba.index(max(y_pred_proba)), (y_test[index] - 1))
            # index starts from 0, but our label starts from 1
            elif y_pred_proba.index(max(y_pred_proba)) != (y_test[index] - 1):
                count_wrong += 1
                # print("wrong, pred, test",(X_test_data[0], X_test_data[1], X_test_data[2]),  train_stat_to_test[(X_test_data[0], X_test_data[1], X_test_data[2])], y_pred_proba.index(max(y_pred_proba)), (y_test[index] - 1))
            else:
                count_correct += 1

        score_all.append(1 - (count_unknown + count_wrong)/len(y_pred))
        iter_count += 1

    print("average score, all scores", mean(score_all), score_all)

    trained_model.fit(X, y)
    today_date = datetime.datetime.today()
    today_date = today_date.strftime("%d-%B-%Y")

    model_dir = "./models/"

    if not os.path.exists(model_dir):
        os.mkdir(model_dir)

    filename = "trained_model.sav"
    timestamped_filename = "{}trained_model_{}.sav".format(model_dir, today_date)
    pickle.dump(trained_model, open(filename, 'wb'))
    pickle.dump(trained_model, open(timestamped_filename, 'wb'))


if __name__ == "__main__":
    main()