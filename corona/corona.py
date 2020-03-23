from pickle import dump, load
from time import localtime, sleep

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from twilio.rest import Client

collection_list = ['TotalCases', 'TotalDeaths', 'TotalRecovered', 'NewDeaths']


def collect_worldometer():
    global column_heads
    URL = 'https://www.worldometers.info/coronavirus/country/us/'

    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')

    results = soup.find(id='usa_table_countries_today')
    test = results.find_all('td')
    column_heads = results.find_all('th')

    # Gets number of columns, in case they change the size of the table
    column_num = len(column_heads)
    
    
    total_stats = []
    for x in collection_list:
        total_stats.append(test[-column_num:][column_get(x)].text.strip())
    
    
    table = []
    list = []

    count = 0
    for x in test:
        if count < column_num:
            list.append(x.text.strip())
        else:
            table.append(list)
            list = []
            list.append(x.text.strip())
            count = 0
        count += 1
    return table, total_stats


def collect_county_count():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--incognito")
    options.binary_location = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser'
    driver_path = '/Users/noumenari/Documents/Python Projects/chromedriver'
    baby_driver = webdriver.Chrome(options=options,
                                   executable_path=driver_path)
    baby_driver.get(
        'https://www.nytimes.com/interactive/2020/us/coronavirus-us-cases.html'
    )

    # Clicks "Show More" button to show all county data
    try:
        element = baby_driver.find_element_by_xpath(
            '//*[@id="coronavirus-us-cases"]/div/div/div[6]/div/button')
        baby_driver.execute_script("arguments[0].click();", element)
    except:
        logging.warning('County data xpath error')
        emergency()

    # Collects county data and transforms it.
    states = baby_driver.find_elements_by_xpath(
        '//*[@id="coronavirus-us-cases"]/div/div/div[6]/div/table')
    county_df = [x for x in states[0].text.split('\n')][1:]

    baby_driver.close()
    return county_df


def main():
    table, total_stats = collect_worldometer()

    county_df = collect_county_count()

    with open('login.p', 'rb') as pfile:
        logins = load(pfile)

    twilioCli = Client(logins[0], logins[1])

    for k in numbers:
        for x in table:
            if x[0] == numbers[k][0]:
                state_case_count = x[column_get(collection_list[0])]
                state_death_count = x[column_get(collection_list[1])]
                state_death_change = x[column_get(collection_list[3])]

        if state_case_count == '':
            state_case_count = '0'
        if state_death_count == '':
            state_death_count = '0'

        for x in county_df:
            if numbers[k][1] in x[len(numbers[k][0]) + 1:]:
                county_count = x.split()[-1]

        # Craft personalized message
        message = 'U.S. Covid-19\nTotal Cases: ' + total_stats[0] + \
            '\nTotal Deaths: ' + total_stats[1]
        if total_stats[3] != '':
            message += ' (+' + total_stats[3] + ')'
        message += '\nTotal Recovered: ' + total_stats[2] + '\n' + \
            numbers[k][0] + ":\nCases: " + state_case_count + "\nDeaths: " + \
            state_death_count
        if state_death_change != '':
            message += ' (' + state_death_change + ')'
        message += "\n" + numbers[k][1] + ":\nCases: " + county_count
        
        message = twilioCli.messages.create(body=message,
                                            from_=logins[2],
                                            to=k)
        
        #print(message)
        #print()
    
    sleep(86400 - localtime()[5])
    main()

def column_get(tem):
    for x in range(len(column_heads)):
        if column_heads[x].text == tem:
            return x


if __name__ == '__main__':
    main()    
