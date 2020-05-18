import os
import sys
import json
import numpy
import matplotlib.pyplot as plt
import aggregate_streaming_stat as ass
from matplotlib.patches import Rectangle

STAT_NAME_TO_INDEX = {
    "avg_joining_time" : 0,
    "avg_playing_bitrates": 1,
    "avg_buffering_percentage" : 2,
    "avg_buffering_events" : 3,
    "avg_seconds_buffered" : 4,
    "avg_estimated_bandwidth" : 5,
    "avg_quality_oscilations" : 6,
    "avg_instability" : 7,
    "avg_loss_rate_client" : 8,
    "avg_loss_rate_server" : 9,
    "avg_gputs_client" : 10,
    "avg_gputs_server" : 11
}

TEST_SET_TO_PLOT_INDEX = {
    "720_cubic_0_0_60" : (0, 4),
    "720_cubic_20_0_60" : (1, 4),
    "720_cubic_40_0_60" : (2, 4),
    "720_cubic_0_0_30" : (3, 4),
    "720_cubic_20_0_30" : (4, 4),
    "720_cubic_40_0_30" : (5, 4),
    "720_cubic_0_0_10" : (6, 4),
    "720_cubic_20_0_10" : (7, 4),
    "720_cubic_40_0_10" : (8, 4),
    "480_cubic_0_0_60": (0, 3),
    "480_cubic_20_0_60": (1, 3),
    "480_cubic_40_0_60": (2, 3),
    "480_cubic_0_0_30": (3, 3),
    "480_cubic_20_0_30": (4, 3),
    "480_cubic_40_0_30": (5, 3),
    "480_cubic_0_0_10": (6, 3),
    "480_cubic_20_0_10": (7, 3),
    "480_cubic_40_0_10": (8, 3),
    "360_cubic_0_0_60": (0, 2),
    "360_cubic_20_0_60": (1, 2),
    "360_cubic_40_0_60": (2, 2),
    "360_cubic_0_0_30": (3, 2),
    "360_cubic_20_0_30": (4, 2),
    "360_cubic_40_0_30": (5, 2),
    "360_cubic_0_0_10": (6, 2),
    "360_cubic_20_0_10": (7, 2),
    "360_cubic_40_0_10": (8, 2),
    "240_cubic_0_0_60": (0, 1),
    "240_cubic_20_0_60": (1, 1),
    "240_cubic_40_0_60": (2, 1),
    "240_cubic_0_0_30": (3, 1),
    "240_cubic_20_0_30": (4, 1),
    "240_cubic_40_0_30": (5, 1),
    "240_cubic_0_0_10": (6, 1),
    "240_cubic_20_0_10": (7, 1),
    "240_cubic_40_0_10": (8, 1),
    "144_cubic_0_0_60": (0, 0),
    "144_cubic_20_0_60": (1, 0),
    "144_cubic_40_0_60": (2, 0),
    "144_cubic_0_0_30": (3, 0),
    "144_cubic_20_0_30": (4, 0),
    "144_cubic_40_0_30": (5, 0),
    "144_cubic_0_0_10": (6, 0),
    "144_cubic_20_0_10": (7, 0),
    "144_cubic_40_0_10": (8, 0),
    "720_bbr_0_0_60" : (9, 4),
    "720_bbr_20_0_60" : (10, 4),
    "720_bbr_40_0_60" : (11, 4),
    "720_bbr_0_0_30" : (12, 4),
    "720_bbr_20_0_30" : (13, 4),
    "720_bbr_40_0_30" : (14, 4),
    "720_bbr_0_0_10" : (15, 4),
    "720_bbr_20_0_10" : (16, 4),
    "720_bbr_40_0_10" : (17, 4),
    "480_bbr_0_0_60": (9, 3),
    "480_bbr_20_0_60": (10, 3),
    "480_bbr_40_0_60": (11, 3),
    "480_bbr_0_0_30": (12, 3),
    "480_bbr_20_0_30": (13, 3),
    "480_bbr_40_0_30": (14, 3),
    "480_bbr_0_0_10": (15, 3),
    "480_bbr_20_0_10": (16, 3),
    "480_bbr_40_0_10": (17, 3),
    "360_bbr_0_0_60": (9, 2),
    "360_bbr_20_0_60": (10, 2),
    "360_bbr_40_0_60": (11, 2),
    "360_bbr_0_0_30": (12, 2),
    "360_bbr_20_0_30": (13, 2),
    "360_bbr_40_0_30": (14, 2),
    "360_bbr_0_0_10": (15, 2),
    "360_bbr_20_0_10": (16, 2),
    "360_bbr_40_0_10": (17, 2),
    "240_bbr_0_0_60": (9, 1),
    "240_bbr_20_0_60": (10, 1),
    "240_bbr_40_0_60": (11, 1),
    "240_bbr_0_0_30": (12, 1),
    "240_bbr_20_0_30": (13, 1),
    "240_bbr_40_0_30": (14, 1),
    "240_bbr_0_0_10": (15, 1),
    "240_bbr_20_0_10": (16, 1),
    "240_bbr_40_0_10": (17, 1),
    "144_bbr_0_0_60": (9, 0),
    "144_bbr_20_0_60": (10, 0),
    "144_bbr_40_0_60": (11, 0),
    "144_bbr_0_0_30": (12, 0),
    "144_bbr_20_0_30": (13, 0),
    "144_bbr_40_0_30": (14, 0),
    "144_bbr_0_0_10": (15, 0),
    "144_bbr_20_0_10": (16, 0),
    "144_bbr_40_0_10": (17, 0)
}

PLOT_TWO_STATS = {
    2: {
        "720_cubic_20_0_60" : (2, 2),
        "720_cubic_20_0_30" : (1, 2),
        "720_cubic_20_0_10" : (0, 2),
        "480_cubic_20_0_60": (2, 1),
        "480_cubic_20_0_30": (1, 1),
        "480_cubic_20_0_10": (0, 1),
        "360_cubic_20_0_60": (2, 0),
        "360_cubic_20_0_30": (1, 0),
        "360_cubic_20_0_10": (0, 0),
        "720_bbr_20_0_60": (5, 2),
        "720_bbr_20_0_30": (4, 2),
        "720_bbr_20_0_10": (3, 2),
        "480_bbr_20_0_60": (5, 1),
        "480_bbr_20_0_30": (4, 1),
        "480_bbr_20_0_10": (3, 1),
        "360_bbr_20_0_60": (5, 0),
        "360_bbr_20_0_30": (4, 0),
        "360_bbr_20_0_10": (3, 0),
    },
    4: {
        "720_cubic_0_0_30": (0, 2),
        "720_cubic_20_0_30": (1, 2),
        "720_cubic_40_0_30": (2, 2),
        "480_cubic_0_0_30": (0, 1),
        "480_cubic_20_0_30": (1, 1),
        "480_cubic_40_0_30": (2, 1),
        "360_cubic_0_0_30": (0, 0),
        "360_cubic_20_0_30": (1, 0),
        "360_cubic_40_0_30": (2, 0),
        "720_bbr_0_0_30": (3, 2),
        "720_bbr_20_0_30": (4, 2),
        "720_bbr_40_0_30": (5, 2),
        "480_bbr_0_0_30": (3, 1),
        "480_bbr_20_0_30": (4, 1),
        "480_bbr_40_0_30": (5, 1),
        "360_bbr_0_0_30": (3, 0),
        "360_bbr_20_0_30": (4, 0),
        "360_bbr_40_0_30": (5, 0),
    }
}


PLOT_ONE_STAT ={
    2: {
        "720_cubic_20_0_60" : (2, 0),
        "720_cubic_20_0_30" : (1, 0),
        "720_cubic_20_0_10" : (0, 0),
        "720_bbr_20_0_60": (5, 0),
        "720_bbr_20_0_30": (4, 0),
        "720_bbr_20_0_10": (3, 0),
    },
    4: {
        "720_cubic_0_0_30": (0, 0),
        "720_cubic_20_0_30": (1, 0),
        "720_cubic_40_0_30": (2, 0),
        "720_bbr_0_0_30": (3, 0),
        "720_bbr_20_0_30": (4, 0),
        "720_bbr_40_0_30": (5, 0),
    }
}


# Plot the relative difference graph, but with only 1 stats (e.g., watermark or headroom)
# The other 2 stats are fixed, i.e., only tests with them set as default value are plotted
# For example, if plot is watermark, only tests with headroom = 20 (default) and quality limit at 720 are considered
def plot_relative_diff_1stat(relative_diff_per_testset, baseline_stat, fixed_index, fixed_value, file_dir, plot_title):

    fig, ax = plt.subplots(figsize=(6, 2), dpi=400)

    rec_size = 0.2

    if not relative_diff_per_testset:
        return

    cmap = plt.get_cmap('coolwarm')

    for testset in relative_diff_per_testset:
        # 720_cubic_20_0_30
        parameters = testset.split("_")
        quality_limit = parameters[0]
        cc = parameters[1]
        headroom = parameters[2]
        watermark = parameters[4]
        if parameters[fixed_index] != fixed_value:
            continue
        if testset not in PLOT_ONE_STAT[fixed_index]:
            continue
        x, y = PLOT_ONE_STAT[fixed_index][testset]
        relative_diff = relative_diff_per_testset[testset]

        ax.add_patch(
            Rectangle((x * rec_size, y * rec_size), width=rec_size, height=rec_size, color=cmap(relative_diff + 0.5),
                      ec=None, lw=None))

    plt.yticks([0.1], ["720"])
    x_ticks = ["10", "30", "60", "10", "30", "60"]
    x_tick_start = (1.2 / len(x_ticks)) / 2
    plt.xticks([(x_tick_start + (1.2 / len(x_ticks)) * i) for i in range(len(x_ticks))],
               x_ticks)
    # plt.axis('off')
    sm = plt.cm.ScalarMappable(cmap=plt.get_cmap('coolwarm'))
    sm._A = []
    cbar = fig.colorbar(sm, ticks=[0, 0.5, 1], orientation='vertical', pad=0.03, shrink=1)
    cbar.ax.set_yticklabels(['< - 100%', round(baseline_stat, 3), '> + 100%'])
    ax.set_xlim([0, 1.2])
    ax.set_ylim([0, 0.2])
    plt.title("cubic             |                bbr")
    plt.savefig(file_dir + '/' + plot_title + '.png', bbox_inches='tight')


# Plot the relative difference graph, but with only 2 stats (e.g., quality and headroom)
# The other stat is fixed, i.e., only tests with that stat set as default value are plotted
# For example, if fixed_stat is watermark, only tests with watermark = 30 (default) are considered
def plot_relative_diff_2stat(relative_diff_per_testset, baseline_stat, fixed_index, fixed_value, file_dir, plot_title):

    fig, ax = plt.subplots(figsize=(6, 4), dpi=400)

    rec_size = 0.2

    if not relative_diff_per_testset:
        return

    cmap = plt.get_cmap('coolwarm')

    for testset in relative_diff_per_testset:
        # 720_cubic_20_0_30
        parameters = testset.split("_")
        quality_limit = parameters[0]
        cc = parameters[1]
        headroom = parameters[2]
        watermark = parameters[4]
        if parameters[fixed_index] != fixed_value:
            continue
        if testset not in PLOT_TWO_STATS[fixed_index]:
            continue
        x, y = PLOT_TWO_STATS[fixed_index][testset]
        relative_diff = relative_diff_per_testset[testset]

        ax.add_patch(
            Rectangle((x * rec_size, y * rec_size), width=rec_size, height=rec_size, color=cmap(relative_diff + 0.5),
                      ec=None, lw=None))

    plt.yticks([0.1, 0.3, 0.5], ["360", "480", "720"])
    x_ticks = ["0%", "20%", "40%", "0%", "20%", "40%"]
    x_tick_start = (1.2 / len(x_ticks)) / 2
    plt.xticks([(x_tick_start + (1.2 / len(x_ticks)) * i) for i in range(len(x_ticks))],
               x_ticks)
    # plt.axis('off')
    sm = plt.cm.ScalarMappable(cmap=plt.get_cmap('coolwarm'))
    sm._A = []
    cbar = fig.colorbar(sm, ticks=[0, 0.5, 1], orientation='vertical', pad=0.03, shrink=1)
    cbar.ax.set_yticklabels(['< - 100%', round(baseline_stat, 3), '> + 100%'])
    ax.set_xlim([0, 1.2])
    ax.set_ylim([0, 0.6])
    plt.title("cubic             |                bbr")
    plt.savefig(file_dir + '/' + plot_title + '.png', bbox_inches='tight')


def plot_relative_diff(relative_diff_per_testset, baseline_stat, file_dir, plot_title):
    fig, ax = plt.subplots(figsize=(16, 6), dpi=400)

    rec_size = 0.1

    if not relative_diff_per_testset:
        return

    cmap = plt.get_cmap('coolwarm')

    for testset in relative_diff_per_testset:
        x = TEST_SET_TO_PLOT_INDEX[testset][0]
        y = TEST_SET_TO_PLOT_INDEX[testset][1]
        relative_diff = relative_diff_per_testset[testset]

        ax.add_patch(Rectangle((x * rec_size, y * rec_size), width=rec_size, height=rec_size, color=cmap(relative_diff + 0.5), ec=None, lw=None))

    plt.yticks([0.05, 0.15, 0.25, 0.35, 0.45], ["144", "240", "360", "480", "720"])
    plt.xticks([0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 1.05, 1.15, 1.25, 1.35, 1.45, 1.55, 1.65, 1.75],
               ["60-0", "60-20", "60-40", "30-0", "30-20", "30-40", "10-0", "10-20", "10-40", "60-0", "60-20", "60-40", "30-0", "30-20", "30-40", "10-0", "10-20", "10-40"])
    # plt.axis('off')
    sm = plt.cm.ScalarMappable(cmap=plt.get_cmap('coolwarm'))
    sm._A = []
    cbar = fig.colorbar(sm, ticks=[0, 0.5, 1], orientation='vertical', pad=0.03, shrink=1)
    cbar.ax.set_yticklabels(['< - 100%', round(baseline_stat, 3), '> + 100%'])
    ax.set_xlim([0, 1.8])
    ax.set_ylim([0, 0.5])
    plt.title("cubic                                            |                                              bbr")
    plt.savefig(file_dir + '/' + plot_title + '.png', bbox_inches='tight')


def main():
    stat = None
    if len(sys.argv) == 2:
        script, all_tests_dir = sys.argv
    elif len(sys.argv) == 3:
        script, all_tests_dir, stat = sys.argv
    else:
        print("\r\n example run: python3 aggregate_streaming_stat.py all_tests_dir [stat]")
        sys.exit(1)

    stat_set = all_tests_dir.split("/")[-1]
    if not stat_set:
        stat_set = all_tests_dir.split("/")[-2]

    if os.path.exists("{}.json".format(stat_set)):
        all_stats = json.load(open("{}.json".format(stat_set), "r"))
    else:
        all_stats = {}
        for one_test_set in os.listdir(all_tests_dir):
            if ".DS" in one_test_set:
               continue
            print("one test set", one_test_set)
            one_test_set_dir = "{}/{}".format(all_tests_dir, one_test_set)
            streaming_stats = ass.aggregate_stat(
                one_test_set_dir)
            all_stats[one_test_set] = streaming_stats

            # avg_joining_time, avg_playing_bitrates, avg_buffering_percentage, avg_buffering_events, avg_seconds_buffered,
            # avg_estimated_bandwidth, avg_quality_oscilations, avg_instability, avg_loss_rate_client, avg_loss_rate_server, avg_gputs_client, avg_gputs_server

        json.dump(all_stats, open("{}.json".format(stat_set), "w"))

    if stat:
        relative_diff_per_testset = {}
        print("RELATIVE STAT FOR ", stat)
        baseline_stat = None
        stat_index = STAT_NAME_TO_INDEX[stat]
        for one_test_set in all_stats.keys():
            # baseline should be 720 cubic 20 0 30
            if one_test_set == "720_cubic_20_0_30":
                baseline_stat = all_stats[one_test_set][stat_index]
                print("baseline stat", stat, baseline_stat)
        for one_test_set in all_stats.keys():
            interested_stat = all_stats[one_test_set][stat_index]
            if not baseline_stat:
                relative_diff = (interested_stat - baseline_stat)
            else:
                relative_diff = (interested_stat - baseline_stat)/baseline_stat
            relative_diff_per_testset[one_test_set] = relative_diff
            print("{} {} {}".format(one_test_set, interested_stat, relative_diff))

        plot_relative_diff(relative_diff_per_testset, baseline_stat, "./", "{}_{}".format(stat_set, stat))
        fixed_index = 2
        fixed_value = "20"
        # plot_relative_diff_2stat(relative_diff_per_testset, baseline_stat, fixed_index, fixed_value, "./", "{}_{}_{}_{}".format(stat_set, stat, fixed_value, fixed_index))

        plot_relative_diff_1stat(relative_diff_per_testset, baseline_stat, fixed_index, fixed_value, "./", "{}_{}_{}_{}".format(stat_set, stat, fixed_value, fixed_index))


if __name__ == "__main__":
    main()
