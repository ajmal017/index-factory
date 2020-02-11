import os
import requests
import logging
import json
from behave import given, when, then
from awscli import clidriver


@given('we have a local serverless instance running')
def step_impl(context):
    result = requests.get('http://127.0.0.1:3000')
    assert result.status_code == 200


@when('we define a new index {index_name} ({index_code}) starting on {year}-{month}-{day} depending on markets {markets}')
def step_impl(context, index_name, index_code, year, month, day, markets):
    index_data = {
        'name': index_name,
        'indexCode': index_code,
        'startDate': '%d%02d%02d' % (int(year), int(month), int(day)),
        'markets': markets.split(',')
    }
    index_json = json.dumps(index_data)
    logging.info('json: %s', index_json)
    response = requests.post('http://127.0.0.1:3000/indices', json=index_json)
    result = json.loads(response.text)
    assert result['indexCode'] == index_code


@when('we upload a CSV file with daily prices as of {year}-{month}-{day} for market {market}')
def step_impl(context, market, year, month, day):

    os.environ['AWS_ACCESS_KEY_ID'] = 'S3RVER'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'S3RVER'
    args = ['--debug', '--endpoint', 'http://127.0.0.1:8001',
            's3api', 'put-object', '--bucket', 'index-factory-daily-prices-bucket',
            '--key', '"US/2020/01/US_20200131.csv"', '--body', 'resources/fake-data/US_20200131.csv']

    status = clidriver.create_clidriver().main(args)
    assert status == 0
    return
    url = "http://localhost:3000/upload-prices/{}".format(market)
    test_prices_path = 'resources/fake-data'
    filename = '{}_{}{}{}.csv'.format(market, year, month, day)
    prices_file = os.path.abspath(os.sep.join([test_prices_path, filename]))
    with open(prices_file, 'rb') as prices:
        response = requests.request('POST', url, files={'prices': prices})
        json_response = json.loads(response.text)
        logging.info('prices upload response: %s', str(json_response))
        assert json_response['partitionKey'] == 'eod-prices#{}'.format(market)
        assert json_response['sortKey'] == 'eod-prices#{}{}{}'.format(year, month, day)


@when('we upload a CSV file with number of shares as of {year}-{month}-{day} for market {market}')
def step_impl(context, market, year, month, day):
    url = "http://localhost:3000/upload-nosh/{}".format(market)
    test_nosh_path = 'resources/fake-data'
    logging.info('url: %s', url)
    filename = '{}_NOSH_{}{}{}.csv'.format(market, year, month, day)
    nosh_file = os.path.abspath(os.sep.join([test_nosh_path, filename]))
    with open(nosh_file, 'rb') as nosh:
        response = requests.request('POST', url, files={'numberOfShares': nosh})
        json_response = json.loads(response.text)
        logging.info('number of shares upload response: %s', str(json_response))
        assert json_response['count'] > 0


@then('querying indices for market {market} returns "{indices}"')
def step_impl(context, market, indices):
    url = "http://localhost:3000/markets/{}".format(market)
    response = requests.request('GET', url)
    json_response = json.loads(response.text)
    logging.info('indices for market %s response: %s', market, str(json_response))
    assert len(json_response['indices']) == len(indices.split(','))
    for item in json_response['indices']:
        assert item['indexCode'] in indices.split(',')


@then('the {index_code} index value is {index_value}')
def step_impl(context, index_code, index_value):
    assert False


@when('we upload a CSV file with dividends as of {year}-{month}-{day} for market {market}')
def step_impl(context, market, year, month, day):
    assert False

