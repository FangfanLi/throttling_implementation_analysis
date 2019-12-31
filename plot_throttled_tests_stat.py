import json
import glob
import os
import sys
import traceback
import reverse_geocode


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


def get_test_files(test_id, wehe_record_dir):
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
    print(mobileStat_file)

    mobileStats = get_mobilestat(replayInfo, mobileStat_file)

    return replayInfo, mobileStats


def loadMobileStats(mobileStats):
    # use mobile stats to locate the geoInfo
    try:
        lat = mobileStats['locationInfo']['latitude']
        lon = mobileStats['locationInfo']['longitude']
        localTime = mobileStats['locationInfo']['localTime']
        ymd = localTime.split(" ")[0]
        hour = localTime.split(" ")[1].split("-")[0]
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
        ymd = hour = ""

    return lat, lon, country, countryCode, city, ymd, hour


def find_meda_data(one_test_id, wehe_record_dir):
    replayInfo, mobileStats = get_test_files(one_test_id, wehe_record_dir)
    if replayInfo:
        lat, lon, country, countryCode, city, ymd, hour = loadMobileStats(mobileStats)
        return (ymd, hour, (lat, lon))
    else:
        return None



def main():

    wehe_record_dir = "/net/data/record-replay/weheRecord/"

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

    print(classified_tests_meta_data)


if __name__ == "__main__":
    main()