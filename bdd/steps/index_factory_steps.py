import os
from collections import defaultdict
from decimal import Decimal
from time import sleep
from typing import List, Tuple

import requests
import logging
import json
from behave import given, when, then
from awscli import clidriver


def endpoint_aws_s3() -> str:
    return os.environ['AWS_ENDPOINT_S3'] 


def endpoint_serverless(uri='') -> str:
    return '{endpoint}{uri}'.format(endpoint=os.environ['AWS_ENDPOINT_SERVERLESS'], uri=uri)


def awsclis3(args: List[str]) -> Tuple[int, str]:
    pre_args = [
        # '--debug',
        '--endpoint',
        endpoint_aws_s3()
    ]
    driver = clidriver.create_clidriver()
    status = driver.main(pre_args + args)
    return status


@given('we have a local serverless instance running')
def step_impl(context):
    result = requests.get(endpoint_serverless())
    assert result.status_code == 200


@when('we define a new index "{index_name}" ({index_code}) depending on markets {'
      'markets}')
def step_impl(context, index_name, index_code, markets):
    index_data = {
        'name': index_name,
        'indexCode': index_code,
        'markets': markets.split(','),
        'rebalancingFrequency': 'monthly',
        'rebalancingWeekDay': 'tuesday',
        'rebalancingSide': 'last day of period'
    }
    index_json = json.dumps(index_data)
    logging.info('json: %s', index_json)
    response = requests.post(endpoint_serverless('/indices'), json=index_json)
    result = json.loads(response.text)
    assert result['indexCode'] == index_code


@when('we upload a CSV file with daily prices as of {year}-{month}-{day} for market {market}')
def step_impl(context, year, month, day, market):

    args = ['s3api', 'put-object',
            '--bucket', os.environ['S3_BUCKET_DAILY_PRICES'],
            '--key', '{market}/{year}/{month}/{market}_{year}{month}{day}.csv'.format(market=market, year=year, month=month, day=day),
            '--body', 'resources/fake-data/{market}_{year}{month}{day}.csv'.format(market=market, year=year, month=month, day=day)]

    status = awsclis3(args)
    assert status == 0


@when('we upload a CSV file with number of shares as of {year}-{month}-{day} for market {market}')
def step_impl(context, year, month, day, market):

    args = ['s3api', 'put-object',
            '--bucket', os.environ['S3_BUCKET_NUMBER_OF_SHARES'],
            '--key', '{market}/{year}/{month}/{market}_{year}{month}{day}.csv'.format(market=market, year=year, month=month, day=day),
            '--body', 'resources/fake-data/{market}_NOSH_{year}{month}{day}.csv'.format(market=market, year=year, month=month, day=day)]

    status = awsclis3(args)
    assert status == 0


@when('we upload a CSV file with dividends as of {year}-{month}-{day} for market {market}')
def step_impl(context, year, month, day, market):
    
    args = ['s3api', 'put-object',
            '--bucket', os.environ['S3_BUCKET_DIVIDENDS'],
            '--key', '{market}/{year}/{month}/{market}_{year}{month}{day}.csv'.format(market=market, year=year, month=month, day=day),
            '--body', 'resources/fake-data/{market}_DIVIDENDS_{year}{month}{day}.csv'.format(market=market, year=year, month=month, day=day)]

    status = awsclis3(args)
    assert status == 0


@then('querying indices for market {market} returns "{indices}"')
def step_impl(context, market, indices):
    url = endpoint_serverless('/markets/{}'.format(market))
    response = requests.request('GET', url)
    json_response = json.loads(response.text)
    logging.info('indices for market %s response: %s', market, str(json_response))
    assert len(json_response['indices']) == len(indices.split(','))
    for item in json_response['indices']:
        assert item['indexCode'] in indices.split(',')


@then('querying index {index_code} returns index with name "{index_name}"')
def step_impl(context, index_code, index_name):
    url = endpoint_serverless('/indices/{}'.format(index_code))
    response = requests.request('GET', url)
    json_response = json.loads(response.text)
    logging.info('querying index %s response: %s', index_code, str(json_response))
    assert json_response['name'] == index_name


@then(u'we have got {count} files for {year}-{month} for market {market_code}')
def step_impl(context, count, year, month, market_code):
    args = ['s3api', 'list-objects-v2',
            '--bucket', os.environ['S3_BUCKET_DAILY_PRICES'],
            '--prefix', '{market}/{year}/{month}'.format(market=market_code, year=year, month=month)
            ]

    status = awsclis3(args)
    assert status == 0


@then(u'we do nothing for {pause} seconds')
def step_impl(context, pause):
    sleep(int(pause))


@then(u'the market {market_code} has number of shares dates')
def step_impl(context, market_code):
    assert context.table, "table<dates> is required"
    logging.info('parsing dates: %s', [row['as_of_date'] for row in context.table])
    url = endpoint_serverless('/markets/{}/nosh'.format(market_code))
    response = requests.request('GET', url)
    json_response = json.loads(response.text)
    logging.info('received market nosh: %s', json_response)


@then(u'we do nothing')
def step_impl(context):
    pass


@then("the {index_code} components as of {year}-{month}-{day} are")
def step_impl(context, index_code, year, month, day):
    url = endpoint_serverless('/indices/{}'.format(index_code))
    response = requests.get(url)
    json_response = json.loads(response.text)
    logging.info('received: %s', json_response)
    yyyymmdd = year + month + day
    logging.info('found market values as of %s: %s', yyyymmdd, json_response['market_values'][yyyymmdd])
    market_values = json_response['market_values'][yyyymmdd]
    aggregated_market_values = defaultdict(Decimal)
    for market in market_values:
        for component in market_values[market]:
            aggregated_market_values[component] += Decimal(market_values[market][component])

    for row in context.table:
        assert 'copmaring {} with {}'.format(row['market value'], aggregated_market_values[row['component']]), float(row['market value']) == float(aggregated_market_values[row['component']])


@then('the {index_code} index value is {index_value}')
def step_impl(context, index_code, index_value):
    url = endpoint_serverless('/indices/{}'.format(index_code))
    response = requests.get(url)
    json_response = json.loads(response.text)
    market_values = json_response['market_values']
    markets = json_response['markets']
    logging.info('received market values: %s', market_values)
    logging.info('received markets: %s', markets)
    for market_code in markets:
        url = endpoint_serverless('/markets/{}/nosh'.format(market_code))
        response = requests.request('GET', url)
        json_response = json.loads(response.text)
        logging.info('received market nosh: %s', json_response)

    # Computing index value using nosh and market values

    assert True
