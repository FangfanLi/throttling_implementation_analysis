'''

This script tests Youtube performance by repeatedly

Few parameters that can be modified:

videoIDs can be replaced with the output of calling getTopYoutubeVideoIDs(n)

doDumps default False, when set to True, will record pcap traces while running each experiment

stoptime default 10, how many seconds the video plays

rounds default 5, how many rounds of test to perform for each video

Inputs are 1. the network being tested 2. Whether you are tethered 3. The browser used for testing
Example usage:
    python automated_youtube_api.py [Network] [YES or NO] [Chrome OR Firefox]
'''

import time, sys, os, random, string, subprocess
from selenium import webdriver
# from selenium.webdriver import ActionChains
# from selenium.webdriver.support.ui import Select
# from selenium.webdriver.chrome.options import Options
import matplotlib.pyplot as plt

import argparse


def drawQualityChangeGraph(bevents, endtime, filename):
    fig, ax = plt.subplots()
    plt.ylim((0, 6.5))

    plt.xlim((0, endtime))

    quality2y = {'tiny': 1, 'small': 2, 'medium': 3, 'large': 4, 'hd720': 5, 'hd1080': 6}

    # The data always starts with buffering events and the second event should be quality change.
    # Otherwise, it is malformed and should be filtered on the server

    currQuality = bevents[1].split(' : ')[1].split(' : ')[0]
    Buffering = True

    # bufferingLines represent when the video was buffering
    bufferingLines = []
    # playingLines represent when the video was playing
    playingLines = []
    # For each pair of events that happened during the streaming (except the last one, which is a special case)
    # There are the following possibilities
    for index in range(len(bevents)):
        event = bevents[index]
        # The next event
        if index == len(bevents) - 1:
            ntimeStamp = endtime
        else:
            ntimeStamp = float(bevents[index + 1].split(' : ')[-1])
        # If this event is buffering
        # Independent of the next event, add an additional line for this buffering event
        if 'Buffering' in event:
            Buffering = True
            timeStamp = float(event.split(' : ')[-1])
            bufferingLines.append(([timeStamp, ntimeStamp], [quality2y[currQuality], quality2y[currQuality]]))

        elif 'Quality change' in event:
            newQuality = event.split(' : ')[1]
            timeStamp = float(event.split(' : ')[-1])
            # Need to add a vertical line from currQuality to newQuality
            # Then a horizontal line until next event
            if Buffering:
                bufferingLines.append(([timeStamp, timeStamp], [quality2y[currQuality], quality2y[newQuality]]))
                bufferingLines.append(([timeStamp, ntimeStamp], [quality2y[newQuality], quality2y[newQuality]]))
            else:
                playingLines.append(([timeStamp, timeStamp], [quality2y[currQuality], quality2y[newQuality]]))
                playingLines.append(([timeStamp, ntimeStamp], [quality2y[newQuality], quality2y[newQuality]]))
            # update current quality
            currQuality = newQuality

        else:
            # An additional line for playing event
            Buffering = False
            timeStamp = float(event.split(' : ')[-1])
            playingLines.append(([timeStamp, ntimeStamp], [quality2y[currQuality], quality2y[currQuality]]))

    for bufferingLine in bufferingLines:
        x1x2 = bufferingLine[0]
        y1y2 = bufferingLine[1]
        plt.plot(x1x2, y1y2, 'k-', color='r', linewidth=3)

    for playingLine in playingLines:
        x1x2 = playingLine[0]
        y1y2 = playingLine[1]
        plt.plot(x1x2, y1y2, 'k-', color='b')

    ax.set_yticklabels(['', 'tiny', 'small', 'medium', 'large', '720P', '1080P'])

    plt.title(filename.split('/')[-1])

    plt.savefig(filename + '.png')


def runOne(results_dir, network, maxquality, cc, headroom, cwnd, watermark, stoptime, i, driver):
    url = "http://wehe-test.meddle.mobi/test.html"
    driver.get(url)
    time.sleep(20)

    url_w_parameter = "http://wehe-test.meddle.mobi/test.html?network={}&maxquality={}&cc={}&headroom={}&cwnd={}&watermark={}&i={}".format(
        network, maxquality,
        cc,
        headroom,
        cwnd,
        watermark,
        i)

    driver.get(url_w_parameter)

    driver.find_element_by_id('my_video_1').click()

    dumpName = '{}_{}_{}_{}_{}_{}_{}_client.pcap'.format(network, maxquality, cc, headroom, cwnd, watermark, i)
    command = ['tcpdump', '-w', "{}/{}".format(results_dir, dumpName)]
    pID = subprocess.Popen(command)

    time.sleep(stoptime)

    driver.find_element_by_id('download').click()
    url = "http://wehe-test.meddle.mobi/test.html?endtests"
    driver.get(url)
    pID.terminate()


def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def enable_download_in_headless_chrome(driver, download_dir):
    # add missing support for chrome "send_command"  to selenium webdriver
    driver.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')

    params = {'cmd': 'Page.setDownloadBehavior', 'params': {'behavior': 'allow', 'downloadPath': download_dir}}
    command_result = driver.execute("send_command", params)

def parseInputs(parser):
    parser.add_argument('--network',
                        help='the network being tested (e.g., WiFi, Verizon)', required=True)
    parser.add_argument('--cc',
                        help='the congestion control algo used (e.g., bbr, cubic)', default="cubic")
    parser.add_argument('--maxquality',
                        help='maximum quality allowed', default="720")
    parser.add_argument('--headroom',
                        help='the headroom used when selecting bitrate', default="0.2")
    parser.add_argument('--cwnd',
                        help='the congestion window clamp', default="0")
    parser.add_argument('--watermark',
                        help='the high water mark', default="30")
    parser.add_argument('--results_dir',
                        help='the location to save results', default='/Users/neufan/Project/throttling_implementation_analysis/video_player/')
    parser.add_argument('--stoptime', type=int,
                        help='the playing time for each video, default 60', default=60)
    parser.add_argument('--rounds', type=int,
                        help='rounds of tests for each video, default 10', default=10)


def main():
    parser = argparse.ArgumentParser(description='the specification for running tests')
    parseInputs(parser)
    args = parser.parse_args()

    network = args.network
    maxquality = args.maxquality
    cc = args.cc
    headroom = args.headroom
    cwnd = args.cwnd
    watermark = args.watermark
    # Running time for each video
    stoptime = int(args.stoptime)
    # Rounds of test for each video
    rounds = args.rounds

    results_dir = "{}/{}".format(args.results_dir, network)
    if not os.path.exists(results_dir):
        os.mkdir(results_dir)

    results_dir = "{}/{}".format(results_dir, cc)
    if not os.path.exists(results_dir):
        os.mkdir(results_dir)

    results_dir = "{}/{}_{}_{}_{}_{}".format(results_dir, maxquality, cc, headroom, cwnd, watermark)
    if not os.path.exists(results_dir):
        os.mkdir(results_dir)

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('headless')
    chrome_options.add_argument("--incognito")
    prefs = {}

    prefs["profile.default_content_settings.popups"] = 0
    prefs["download.default_directory"] = results_dir
    chrome_options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome('/Users/neufan/Downloads/chromedriver', chrome_options=chrome_options)
    enable_download_in_headless_chrome(driver, results_dir)

    for i in range(rounds):
        print('\t'.join(map(str, [i, network, maxquality, cc, headroom, cwnd, watermark])))
        runOne(results_dir, network, maxquality, cc, headroom, cwnd, watermark, stoptime, i, driver)
        time.sleep(3)
        driver.close()
        driver = webdriver.Chrome('/Users/neufan/Downloads/chromedriver', chrome_options=chrome_options)
        enable_download_in_headless_chrome(driver, results_dir)

    if driver:
        driver.quit()


if __name__ == "__main__":
    main()
