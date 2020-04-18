"""
US Covid-19 Statistic Webscraper
"""
import logging
from multiprocessing import Pool
from time import localtime, sleep
from datetime import date, timedelta

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from sqlalchemy import create_engine

from corona_accounts import Account, emergency

logging.basicConfig(filename='corona.log',
                    filemode='w',
                    format='%(asctime)s - %(message)s',
                    level=logging.INFO)

# For collection on Raspberry Pi
BROWSER = "/usr/bin/chromium-browser"
DRIVER = "chromedriver"

MAIN_URL = 'https://coronavirus.1point3acres.com/en'
MAIN_XPATH_ROOT = '//*[@id="__next"]/div/div[9]'

BAY_URL = 'https://projects.sfchronicle.com/2020/coronavirus-map/'
DATABASE = 'sqlite:///corona-database.db'


class WebsiteChanged(Exception):
    pass


def create_driver():
    options = Options()
    options.headless = True
    options.add_argument('--incognito')
    options.binary_location = BROWSER
    driver_path = DRIVER
    return webdriver.Chrome(options=options, executable_path=driver_path)


def collect_main_data(_):
    """
    Collects data from: https://coronavirus.1point3acres.com/en
    and stores it in a pandas dataframe.
    """
    logging.info('collect_main_data started.')
    with create_driver() as main_driver:
        main_driver.get(MAIN_URL)

        # Collect State Data
        states = main_driver.find_elements_by_xpath(
            MAIN_XPATH_ROOT)[0].text.split('\n')
        state_data_list = [
            x.strip().replace(',', '') for x in states
            if x[0] != '+' and x[0] != '-' and x[-1] != '%'
        ]

        #  Starts collection when it reads "New York." First state on the list.
        for x in range(len(state_data_list)):
            if state_data_list[x] == 'New York':
                state_data_list = state_data_list[x:]
                break
        try:
            header = main_driver.find_elements_by_xpath(
                MAIN_XPATH_ROOT + '/header')[0].text.split('\n')
        except IndexError as err:
            main_driver.close()
            logging.info(f'Website changed xpath: {MAIN_URL}')
            emergency(f'Website changed xpath: {MAIN_URL}')
            raise WebsiteChanged(err)

        for ind, col in enumerate(header):
            if col.lower() == 'fatality rate' or col.lower() == 'fatality':
                header.pop(ind)
        header_size = len(header)

        #  Stores collected state data in a Pandas dataframe
        state_data_df = pd.DataFrame([
            state_data_list[x:x + header_size:]
            for x in range(0, len(state_data_list), header_size)
        ],
            columns=header)

        #  Creates an empty dataframe for county data
        main_data = pd.DataFrame(columns=[
            'state', 'county', 'county_cases',
            'county_deaths', 'county_recovered'
        ])

        #  Loops through each state on the website and stores county data
        for x in range(2, len(state_data_df) + 1):

            # Clicks "Show More" button to show all county data
            drop_down = main_driver.find_element_by_xpath(
                f'{MAIN_XPATH_ROOT}/div[{x}]/div/span[1]')
            main_driver.execute_script('arguments[0].click();', drop_down)

            # Collects county data and transforms it.
            counties = main_driver.find_elements_by_xpath(
                f'{MAIN_XPATH_ROOT}/div[{x}]/div[2]')[0].text.split('\n')
            county_data_list = [
                y.strip().replace(',', '') for y in counties
                if y[0] != '+' and y[0] != '-' and y[-1] != '%'
            ]

            # Close county data to increase performance
            main_driver.execute_script('arguments[0].click();', drop_down)

            df_to_append = pd.DataFrame([
                county_data_list[y:y + header_size:]
                for y in range(0, len(county_data_list), header_size)
            ],
                columns=[
                'county', 'county_cases', 'county_deaths',
                'county_recovered'
            ])
            df_to_append['state'] = state_data_df['Location'][x - 2]
            df_to_append['state_cases'] = state_data_df['Cases'][x - 2]
            df_to_append['state_deaths'] = state_data_df['Deaths'][x - 2]
            df_to_append['state_recovered'] = state_data_df['Recovered'][x - 2]
            main_data = main_data.append(df_to_append)

        logging.info('collect_data ended')
        return main_data


def bay_area_collection(_):
    """
    Collects data from: https://projects.sfchronicle.com/2020/coronavirus-map/
    Website provides a Bay Area count similar to how NYC is handled in the
    main data that is a more accurate representation of the data.
    """
    logging.info('bay_area_collection beginning.')
    with create_driver() as bay_area_driver:
        bay_area_driver.get(BAY_URL)

        try:
            bay_area_data = bay_area_driver.find_elements_by_xpath(
                '//*[@id="gatsby-focus-wrapper"]/main/div[2]/section/div[1]'
            )[0].text.split('\n')
        except IndexError as err:
            bay_area_driver.close()
            logging.info(f'Website changed xpath: {BAY_URL}')
            emergency(f'Website changed xpath: {BAY_URL}')
            raise WebsiteChanged(err)

        # Slightly faster than list comprehension
        bay_area_data_parsed = list(
            map(lambda x: x.replace(',', ''),
                bay_area_data[1::3]))

        logging.info('bay_area_collection finished.')
        return bay_area_data_parsed


def add_bay_area(main_data, bay_area):
    logging.info('Adding Bay Area data to main dataframe.')
    temp_df = main_data[main_data['county'] ==
                        'San Francisco'].reset_index(drop=True)
    temp_df['county'] = 'Bay Area'
    temp_df['county_cases'] = bay_area[0]
    temp_df['county_deaths'] = bay_area[1]
    return temp_df


def calculate_time():
    """
    Used to set activiation time to 8pmEST
    """
    eight = (20 * 60 * 60)  # - 120  # 7:58pmEST

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
    logging.info('Beginning sleep till 7:58')
    seven = calculate_time() - 120
    # if time is between 7:58 and 8 then skip sleep
    if seven > 0:
        sleep(seven)  # 7:58

    # Splits website collection into two processes to run simultaniously
    logging.info('Beginning multipooling.')
    p = Pool()
    data = p.map_async(collect_main_data, [1])
    bay = p.map_async(bay_area_collection, [1])
    p.close()
    p.join()

    # collects data from multiprocess pool
    main_data = data.get()[0].reset_index(drop=True)
    bay_area = bay.get()[0]

    # Appends bay area data to bottom of main data.
    main_data = main_data.append(
        add_bay_area(main_data, bay_area), ignore_index=True)
    main_data["date"] = str(date.today())

    logging.info('Beginning sleep till 8.')
    sleep(calculate_time())

    # Opens database to retrieve prior data and account information.
    logging.info('Starting database engine.')
    engine = create_engine('sqlite:///corona-database.db')
    with engine.connect() as connection:
        accounts = tuple(connection.execute('SELECT * FROM Accounts'))

    # Read only prior day data from database
    yesterdate = (date.today() - timedelta(1))
    sql = f'SELECT * FROM cases WHERE date="{str(yesterdate)}"'
    prior_data = pd.read_sql_query(sql, con=engine)

    # Loops through accounts one by one storing relevant data.
    logging.info('Beginning creation of individual data.')
    for account in accounts:
        recipient = Account(*account)
        recipient.set_data(main_data, prior_data)
        logging.info('Sending message to: ' + recipient.number)
        recipient.send_sms()

    # Appends new data to database.
    main_data.to_sql(name='cases', if_exists='append', con=engine, index=False)

    # Closes database connection.
    engine.dispose()
    logging.info('Engine closed.')
    main()


if __name__ == '__main__':
    main()
