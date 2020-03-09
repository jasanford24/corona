from datetime import datetime
from time import sleep

from pyperclip import copy
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Scrapes delegate count from google.
# May only work while he's in second place.
# Will require further testing.


def bernie_delegates():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--incognito")
    options.binary_location = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser'
    driver_path = '/Users/noumenari/Documents/Python Projects/chromedriver'
    browser = webdriver.Chrome(options=options, executable_path=driver_path)

    browser.get(
        'https://www.google.com/search?q=bernie+delegates&oq=bernie+delegates&aqs=chrome..69i57j69i60.6654j0j1&sourceid=chrome&ie=UTF-8'
    )

    temp = browser.find_elements_by_css_selector('.kH9vZe > td:nth-child(3)')
    test = temp[0].text
    browser.close()
    return int(test)


# Load previously collected date/delegate data
def load_data():
    from pickle import load
    with open('delegate.p', 'rb') as pfile:
        return load(pfile)


if __name__ == "__main__":
    # Load datetime, date delegate totals
    del_df = load_data()

    # Webscrape Bernie's current delegate count
    bernie_count = bernie_delegates()

    # Calculate remaining number of available delegates
    remaining = sum(del_df[del_df.datetime > datetime.today()]['delegates'])

    # Calculate percentage of remaining delegates needed for Bernie to reach 1991
    delegate_percent = round((1991 - bernie_count) / remaining, 3)

    # Package it in a neat format for sharing
    answer = '(1991-' + str(bernie_count) + ')/' + \
        str(remaining) + ' = ' + str(delegate_percent) + \
        ' = ' + str(round(delegate_percent*100, 1)) + '% needed'

    # For easily sharing results with friends
    copy(answer)

    print(answer)
