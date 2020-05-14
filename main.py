from app.twitch_client import TwitchClient, get_userinfo
import logging
from time import perf_counter
import json

# Create a new logger instance for this application
logger = logging.getLogger()


# This is just a demo; also useful for debugging.
def main():
    n_followers = 100
    n_followings = 50
    start_time = perf_counter()

    # foo = get_userinfo('adfasfesf')
    print('')
    # streamer_uid = get_userinfo('adfaadsfasfd')
    # streamer_uid = get_userinfo('data_day_life')['uid']
    streamer_uid = get_userinfo('stroopc')['uid']
    # streamer_uid = get_userinfo('prod3x')['uid']      # has zero total followers
    # streamer_uid = get_userinfo('moJohat')['uid']     # has nine total followers

    tc = TwitchClient(streamer_uid, n_followers, n_followings)

    # Check: get followers for streamer
    followers = tc.get_streamer_followers()
    print(followers)

    # Check: get followers followings for streamer
    # followings_count = tc.get_followers_followings()
    # print(followings_count)
    # print(len(followings_count))

    # Check:  Live Stream Collection
    # sim_streams = [('123021305', 0.10212765957446808), ('518869375', 0.06779661016949153),
    # ('485300436', 0.06493506493506493), ('191824389', 0.06285714285714286),
    # ('518767073', 0.06201550387596899), ('518867611', 0.061068702290076333),
    # ('507722450', 0.05852962169878658), ('214990683', 0.05755395683453238),
    # ('513840623', 0.055944055944055944), ('224649547', 0.0547945205479452),
    # ('62670274', 0.05333333333333334), ('518389578', 0.052980132450331126),
    # ('50915147', 0.05161290322580645), ('466770055', 0.051470588235294115), ]
    # candidates = [candidate[0] for candidate in sim_streams]
    # print(candidates)
    # print(tc.get_live_streams(candidates))
    # print(tc.get_prof_img_url(candidates))

    # Check: whole enchilada
    final_results = tc.get_similar_streams()

    print(f'Run time: {perf_counter() - start_time}')
    print(json.dumps(final_results, indent=2))


def logging_setup():
    # logger = logging.getLogger()
    # Set the logging level for this application
    logger.setLevel(logging.DEBUG)

    # Create file handler which logs event debug messages
    log_file_path = 'logs/main.py.log'
    fh = logging.FileHandler(log_file_path, encoding="'utf-8'")
    fh.setLevel(logging.INFO)

    # Create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Create a formatter
    log_display_format = '%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s'
    log_date_format = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(fmt=log_display_format, datefmt=log_date_format)

    # Add formatter to handlers
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    # Add Starting Message and Line Break
    # logger.info('Starting new run of {}'.format(__name__))


if __name__ == "__main__":
    logging_setup()
    main()
