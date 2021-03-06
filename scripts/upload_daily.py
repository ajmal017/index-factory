import requests
import os
import sys
import logging


def main():
    url = "http://localhost:3000/upload-prices/nyse"
    test_prices_path = 'nyse-2018'
    for filename in os.listdir(test_prices_path):
        if not filename.endswith('.csv'):
            continue

        prices_file = os.path.abspath(os.sep.join([test_prices_path, filename]))
        prices = open(prices_file, 'rb')
        response = requests.request("POST", url, files={'prices': prices})
        print(response.text)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(name)s:%(levelname)s:%(message)s')
    logname = os.path.abspath(sys.argv[0]).split(os.sep)[-1].split(".")[0]
    file_handler = logging.FileHandler(logname + '.log', mode='w')
    formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)
    try:
        main()

    except SystemExit:
        pass
    except:
        logging.exception('error occurred', sys.exc_info()[0])
        raise
