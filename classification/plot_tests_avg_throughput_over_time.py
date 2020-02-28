import json
import glob
import os
import sys
import traceback
import statistics
import reverse_geocode
import datetime
from shapely.geometry import Point
from datetime import datetime as dt
import geopandas as gpd
import matplotlib.pyplot as plt


def readStatesPolygon():
    df = gpd.read_file("cb_2017_us_state_500k.shp")

    statesPolygons = {}

    for index, row in df.iterrows():
        statesPolygons[row['STUSPS']] = row['geometry']

    return statesPolygons


def get_US_states(longitude, latitude):
    statesPolygons = readStatesPolygon()
    geoPoint = Point(longitude, latitude)

    for state in statesPolygons:
        if geoPoint.within(statesPolygons[state]):
            return state

    return ''


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


def get_avg_avg_diff_per_day(classified_tests_meta_data):
    avg_diff_per_day = {}
    for one_test_id in classified_tests_meta_data:
        one_test = classified_tests_meta_data[one_test_id]
        #
        ymd = one_test[6]
        if ymd not in avg_diff_per_day:
            avg_diff_per_day[ymd] = []
        # append the average throughput difference
        avg_diff_per_day[ymd].append((one_test[0] - one_test[1]))

    avg_avg_diff_per_class_per_day = {}
    for ymd in avg_diff_per_day:
        avg_avg_diff = statistics.mean(avg_diff_per_day[ymd])
        avg_avg_diff_per_class_per_day[ymd] = avg_avg_diff

    return avg_avg_diff_per_class_per_day


def plot_avg_avg_diff_over_time(classified_tests_meta_data, ISP_replay):
    stat_per_per_day = get_avg_avg_diff_per_day(classified_tests_meta_data)
    # all_color = ['#a6611a', '#018571', '#ca0020', '#0571b0', "#404040"]
    fig, ax = plt.subplots()
    all_dates = list(stat_per_per_day.keys())
    all_dates.sort(key=lambda date: datetime.datetime.strptime(date, '%Y-%m-%d'))
    all_avg_avg_diff = []
    all_dates_plot = []
    for one_date in all_dates:
        dateFormatted = dt.strptime(one_date, '%Y-%m-%d').date()
        all_dates_plot.append(dateFormatted)
        all_avg_avg_diff.append(stat_per_per_day[one_date])

    plt.plot(all_dates_plot, all_avg_avg_diff, label="avg avg diff", linewidth=1, alpha=0.5)

    fig.autofmt_xdate()
    plt.legend(prop={'size': 15})
    fig.tight_layout()
    plt.savefig('{}_avg_avg_dff.png'.format(ISP_replay),
                bbox_inches='tight')
    plt.cla()
    plt.clf()
    plt.close('all')


def main():

    try:
        tests_file = sys.argv[1]
    except:
        print(
            "\r\n Please provide the following input: [classified_tests_file]")
        sys.exit()

    # load tests, i.e., test_stat_per_carrier_replay
    throttled_tests = json.load(open(tests_file, "r"))

    throttled_tests_stat = {}
    # tests are separated by classification results
    for isp_replay in throttled_tests.keys():
        plot_avg_avg_diff_over_time(throttled_tests[isp_replay], isp_replay)

    json.dump(throttled_tests_stat, open("throttled_tests_stat.json", "w"))


if __name__ == "__main__":
    main()