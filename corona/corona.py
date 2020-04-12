#  Raspberry Pi 4B Version

from os import environ
import logging
from multiprocessing import Pool
from time import localtime, sleep

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from sqlalchemy import create_engine
from twilio.rest import Client
from corona_accounts import Account

logging.basicConfig(filename='corona.log',
                    filemode='w',
                    format='%(asctime)s - %(message)s',
                    level=logging.INFO)


#  Collects data from:
#  https://coronavirus.1point3acres.com/en
#  and stores it in a dataframe.
def collect_data(_):
    logging.info("Beginning collect_data.")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--incognito")
    options.binary_location = '/usr/bin/chromium-browser'
    driver_path = 'chromedriver'
    baby_driver = webdriver.Chrome(options=options,
                                   executable_path=driver_path)
    baby_driver.get('https://coronavirus.1point3acres.com/en')
    xpath_base = '//*[@id="__next"]/div/div[8]'

    logging.info("collect_data begin collecting state data.")
    # Collect State Data
    states = baby_driver.find_elements_by_xpath(xpath_base)
    state_df = [
        x.strip().replace(',', '') for x in states[0].text.split('\n')
        if "+" not in x and "%" not in x
    ]

    #  Starts collection when it reads "New York" the first state on the list.
    for index, info in enumerate(state_df):
        if info == "New York":
            state_df = state_df[index:]
            break

    # Collect and Calculate number of headers
    header = baby_driver.find_elements_by_xpath(xpath_base + '/header')
    header = header[0].text.split('\n')
    for index, head in enumerate(header):
        if head.lower() == "fatality rate" or head.lower() == "fatality":
            header.pop(index)
    header_size = len(header)

    #  Stores collected state data in a Pandas dataframe
    state_data = pd.DataFrame(
        [state_df[x:x + header_size:] for x in range(0, len(state_df), header_size)],
        columns=header)
    logging.info("collect_data finished collecting state data.")
    #  Creates an empty dataframe for county data
    data = pd.DataFrame(columns=['state', 'county', 'county_cases', 'county_deaths', 'county_recovered'])

    logging.info("Begin collecting county data.")
    #  Loops through each state on the website and stores county data
    for x in range(2, len(state_data) + 1):
        logging.info("Collecting " + str(x))
        # Clicks "Show More" button to show all county data
        element = baby_driver.find_element_by_xpath(
            f'{xpath_base}/div[{x}]/div/span[1]')
        baby_driver.execute_script("arguments[0].click();", element)

        # Collects county data and transforms it.
        states = baby_driver.find_elements_by_xpath(
            f'{xpath_base}/div[{x}]/div[2]')
        county_df = [
            y.strip().replace(',', '') for y in states[0].text.split('\n')
            if "+" not in y and "%" not in y
        ]

        # Close county data to increase performance
        element = baby_driver.find_element_by_xpath(
            f'{xpath_base}/div[{x}]/div/span[1]')
        baby_driver.execute_script("arguments[0].click();", element)

        temp_data = pd.DataFrame(
            [county_df[y:y + header_size:] for y in range(0, len(county_df), header_size)],
            columns=['county', 'county_cases', 'county_deaths', 'county_recovered'])
        temp_data['state'] = state_data['Location'][x - 2]
        temp_data['state_cases'] = state_data['Cases'][x - 2]
        temp_data['state_deaths'] = state_data['Deaths'][x - 2]
        temp_data['state_recovered'] = state_data['Recovered'][x - 2]
        data = data.append(temp_data)

    baby_driver.close()
    logging.info("collect_data complete.")
    return data


# Prior collection does not combine the bay area into one like it does with New York City
# So added this so San Francisco can have a Bay Area count.
def bay_area_collection(_):
    logging.info("Beginning bay_area_collection.")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--incognito")
    options.binary_location = '/usr/bin/chromium-browser'
    driver_path = 'chromedriver'
    bay_driver = webdriver.Chrome(options=options,
                                   executable_path=driver_path)
    bay_driver.get('https://projects.sfchronicle.com/2020/coronavirus-map/')
    logging.info("bay_area_collection begin parsing info.")
    states = bay_driver.find_elements_by_xpath(
        '//*[@id="gatsby-focus-wrapper"]/main/div[2]/section/div[1]')

    logging.info("bay_area_collection convert data")
    # Slightly faster than list comprehension
    bay_temp = list(
        map(lambda x: x.replace(',', ''), states[0].text.split('\n')[1::2]))
    logging.info("bay_area_collection done converting data.")
    bay_driver.close()
    logging.info("bay_area_collection complete.")
    return bay_temp


# San Francisco in data does not represent an accurate depiction
# so adding data scraped from different website.
# Adds Bay Area data to data dataframe
def add_bay_area(data, bay_area):
    temp = data[data['county'] == 'San Francisco'].reset_index(drop=True)
    temp['county'] = 'Bay Area'
    temp['county_cases'] = bay_area[0]
    temp['county_deaths'] = bay_area[1]
    return temp


# Used to set activiation time to 8pmEST
def calculate_time():
    eight = (20 * 60 * 60) - 60  #7:58pm

    day = 24 * 60 * 60
    hour = (60 * 60) * localtime()[3]
    minute = (60 * localtime()[4])
    second = localtime()[5]

    time_to_sleep = eight - (hour + minute + second)
    if time_to_sleep < 0:
        return day + time_to_sleep
    return time_to_sleep


def main():
    # Sleeps progrm until 7:58pmEST
    logging.info("Beginning sleep.")
    sleep(calculate_time())

    # Splits website collection into two processes to run simultaniously
    logging.info("Beginning multipooling.")
    p = Pool()
    data = p.map_async(collect_data, [1])
    bay = p.map_async(bay_area_collection, [1])
    p.close()
    p.join()

    # collects data from multiprocess pool
    data = data.get()[0].reset_index(drop=True)
    bay_area = bay.get()[0]

    # Appends bay area data to bottom of main data.
    logging.info("Appending data.")
    data = data.append(add_bay_area(data, bay_area), ignore_index=True)

    # Opens database to retrieve prior data and account information.
    logging.info("Starting database engine.")
    engine = create_engine('sqlite:///corona-database.db')
    connection = engine.connect()

    #  Reads prior data and account data
    prior = pd.read_sql_table(table_name='cases', con=engine)
    accounts = tuple(connection.execute("SELECT * FROM Accounts"))

    # Loops through accounts one by one storing relevant data.
    logging.info("Beginning creation of individual data.")
    for x in accounts:
        recipient = Account(*x)
        recipient.set_data(data, prior)
        logging.info("Sending message to: " + recipient.number)
        recipient.send_sms()

    # Stores new data, overwriting previous data.
    data.to_sql(name='cases', if_exists='replace', con=engine, index=False)

    # Closes database connections.
    connection.close()
    engine.dispose()
    logging.info("Engine closed.")
    main()


if __name__ == "__main__":
    main()
