from pickle import dump, load
from time import localtime, sleep

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from twilio.rest import Client


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

    table = []
    list = []
    count = 0

    for x in column_heads:
        list.append(x.text.strip())

    table.append(list)
    list = []

    for x in test:
        if count < column_num:
            list.append(x.text.strip())
        else:
            table.append(list)
            list = []
            list.append(x.text.strip())
            count = 0
        count += 1

    table = [x[:-1] for x in table]
    table = pd.DataFrame(table[1:], columns=table[0])
    
    return table


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
        emergency()

    # Collects county data and transforms it.
    states = baby_driver.find_elements_by_xpath(
        '//*[@id="coronavirus-us-cases"]/div/div/div[6]/div/table')
    county_df = [x for x in states[0].text.split('\n')][1:]

    baby_driver.close()
    return county_df


class Account:
    
    def __init__(self, number, state, county):
        self.number = number
        self.state = state
        self.county = county
        self.message = ''
        self.total_cases = '0'
        self.total_deaths = '0'
        self.new_deaths = '0'
        self.state_case_count = '0'
        self.state_death_count = '0'
        self.county_case_count = '0'
    
    
    def set_state_data(self, table):
        self.total_cases = sum([int(x.replace(',','')) for x in table['TotalCases'] if x != ''])
        self.total_deaths = sum([int(x.replace(',','')) for x in table['TotalDeaths'] if x != ''])
        self.new_deaths = sum([int(x.replace(',','')) for x in table['NewDeaths'] if x != ''])
        
        for index, row in table.iterrows():
            if row['USAState'] == self.state:
                if row['TotalCases'] != '':
                    self.state_case_count = row['TotalCases']
                if row['TotalDeaths'] != '':
                    self.state_death_count = row['TotalDeaths']
    
    def set_county_data(self, county_df):
        for x in county_df:
            t = len(self.state) + 1
            if self.county == x[t:t + len(self.county)]:
                self.county_case_count = x.split()[-1]
    
    def build_message(self):
        message  = 'U.S. Covid-19'
        message += '\nTotal Cases: ' + f"{self.total_cases:,d}"
        message += '\nTotal Deaths: ' + f"{self.total_deaths:,d}" + ' (+' + f"{self.new_deaths:,d}" + ')'
        message += '\n' + self.state + ':'
        message += '\nCases: ' + self.state_case_count
        message += '\nDeaths: ' + self.state_death_count
        message += "\n" + self.county + ":"
        message += "\nCases: " + self.county_case_count
        self.message = message
    
    
    def send_sms(self):
        twilioCli.messages.create(body=self.message,
                                  from_=logins[2],
                                  to=self.number)



# If an error occurs during data collection.
# Sends me a text and shuts program down.
def emergency():
    from sys import exit

    logins = login()
    twilioCli = Client(logins[0], logins[1])

    message = twilioCli.messages.create(
        body="Something has gone wrong.",
        from_=logins[2],
        to=logins[3])
    exit()



def main():
    county_df = collect_county_count()


    with open('login.p', 'rb') as pfile:
        logins = load(pfile)
    

    for x in accounts:
        recipient = Account(*x)
        recipient.set_state_data(collect_worldometer())
        recipient.set_county_data(county_df)
        recipient.build_message()
        recipient.message()
        print()
        #recipient.send_sms()


if __name__=="__main__":
    main()
