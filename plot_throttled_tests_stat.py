import json
import glob
import os
import sys
import traceback
import reverse_geocode
import matplotlib
import datetime
from datetime import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def get_file_from_partial_name(file_partial_name):
    file_name = glob.glob(file_partial_name)
    if file_name:
        return file_name[0]
    else:
        return None


def get_mobilestat(replayInfo, mobileStatsFile):
    # if no mobile stat in replayInfo[14]
    if not replayInfo[14]:
        mobileStats = loadMobileStatsFile(mobileStatsFile)
    else:
        mobileStats = json.loads(replayInfo[14])

    return mobileStats


# Load mobile Stats from mobileStat file (after separating the metadata connection)
def loadMobileStatsFile(mobileStatsFile):
    try:
        mobileStatsJson = mobileStatsFile
        if os.path.exists(mobileStatsJson):
            mobileStatsString = json.load(open(mobileStatsJson, 'r'))
            mobileStats = json.loads(mobileStatsString)
        else:
            return False
    except:
        traceback.print_exc(file=sys.stdout)
        return False

    return mobileStats


def get_test_stat(test_id, wehe_record_dir):
    userID = test_id.split("_")[0]
    historyCount = test_id.split("_")[1]
    user_dir = wehe_record_dir + "/" + userID + "/"
    replayInfo_dir = user_dir + "/replayInfo/"
    mobileStat_dir = user_dir + "/mobileStats/"

    regex_replayInfo_file = "{}/replayInfo_{}_{}_0.json".format(replayInfo_dir, userID, historyCount)
    regex_mobileStat_file = "{}/mobileStats_{}_{}_0.json".format(mobileStat_dir, userID, historyCount)

    replayInfo_file = get_file_from_partial_name(regex_replayInfo_file)
    mobileStat_file = get_file_from_partial_name(regex_mobileStat_file)
    if not replayInfo_file:
        print("\r\n no replayInfo_file", replayInfo_file)
        return None, None

    replayInfo = json.load(open(replayInfo_file, 'r'))
    mobileStats = get_mobilestat(replayInfo, mobileStat_file)

    return replayInfo, mobileStats


def loadMobileStats(mobileStats):
    # use mobile stats to locate the geoInfo
    try:
        lat = mobileStats['locationInfo']['latitude']
        lon = mobileStats['locationInfo']['longitude']
        # later version of the replay server stores location info in replayInfo file
        if 'country' in mobileStats['locationInfo'] and 'countryCode' in mobileStats['locationInfo'] and lat:
            lat = float("{0:.1f}".format(float(lat)))
            lon = float("{0:.1f}".format(float(lon)))
            country = mobileStats['locationInfo']['country']
            city = mobileStats['locationInfo']['city']
            countryCode = mobileStats['locationInfo']['countryCode']
        elif (lat == lon == '0.0') or (lat == lon == 0.0) or (lat == 'nil') or (lat == 'null'):
            lat = lon = ''
            country = ''
            city = ''
            countryCode = ''
        elif lat:
            coordinates = [(float(lat), float(lon))]
            geoInfo = reverse_geocode.search(coordinates)[0]
            country = geoInfo['country']
            city = geoInfo['city']
            countryCode = geoInfo['country_code'].lower()
            lat = float("{0:.1f}".format(float(lat)))
            lon = float("{0:.1f}".format(float(lon)))
        else:
            lat = lon = country = countryCode = city = ''

    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        country = ''
        city = ''
        countryCode = ''
        lat = lon = ''

    return lat, lon, country, countryCode, city


def find_meda_data(one_test_id, wehe_record_dir):
    replayInfo, mobileStats = get_test_stat(one_test_id, wehe_record_dir)
    if mobileStats:
        lat, lon, country, countryCode, city = loadMobileStats(mobileStats)
        try:
            localTime = mobileStats['locationInfo']['localTime']
        except:
            localTime = replayInfo[0]

        ymd = localTime.split(" ")[0]
        hour = localTime.split(" ")[1].split("-")[0]

        return (ymd, hour, (lat, lon))
    else:
        return None


def get_tests_per_day(classified_tests_meta_data):
    tests_per_class_per_day = {}
    for one_class in classified_tests_meta_data:
        tests_per_class_per_day[one_class] = {}
        for one_test in classified_tests_meta_data[one_class]:
            ymd = one_test[0]
            if ymd not in tests_per_class_per_day[one_class]:
                tests_per_class_per_day[one_class][ymd] = 0
            tests_per_class_per_day[one_class][ymd] += 1

    return tests_per_class_per_day


def plot_classification_over_time(classified_tests_meta_data):
    tests_per_class_per_day = get_tests_per_day(classified_tests_meta_data)
    all_color = ['#a6611a', '#018571', '#ca0020', '#0571b0', "#404040"]
    fig, ax = plt.subplots()
    for one_class in tests_per_class_per_day:
        all_dates = list(tests_per_class_per_day[one_class].keys())
        all_dates.sort(key=lambda date: datetime.datetime.strptime(date, '%Y-%m-%d'))
        all_num_tests = []
        all_dates_plot = []
        for one_date in all_dates:
            dateFormatted = dt.strptime(one_date, '%Y-%m-%d').date()
            all_dates_plot.append(dateFormatted)
            all_num_tests.append(tests_per_class_per_day[one_class][one_date])

        if one_class != "unknown":
            color_ind = int(one_class)
        else:
            color_ind = 4

        plt.plot(all_dates_plot, all_num_tests, label="{}".format(one_class), linewidth=1, alpha=0.5, color=all_color[color_ind])

    fig.autofmt_xdate()
    plt.legend(prop={'size': 15})
    fig.tight_layout()
    plt.savefig('{}_xPutsCDF.png'.format("yt_att"),
                bbox_inches='tight')
    plt.cla()
    plt.clf()
    plt.close('all')


def main():

    try:
        wehe_record_dir = sys.argv[1]
    except:
        print(
            "\r\n Please provide the following input: [wehe_record_dir]")
        sys.exit()

    classified_tests_meta_data = {}
    # load tests
    classified_tests_file = "review_tests_yt_att.json"
    classified_tests = json.load(open(classified_tests_file, "r"))
    # tests are separated by classification results
    for classification in classified_tests:
        classified_tests_meta_data[classification] = []
        for one_test_id in classified_tests[classification]:
            # find metadata for this test
            # (ymd, hour, (lat, lon))
            meta_data = find_meda_data(one_test_id, wehe_record_dir)
            if meta_data:
                classified_tests_meta_data[classification].append(meta_data)

    plot_classification_over_time(classified_tests_meta_data)


if __name__ == "__main__":
    main()