#import libraries
#libraries subection 1
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
#libraries subsection 2
import pandas as pd
import pickle
import datetime
import re

start_time = time.time()
#changing chromedriver default options
options = Options()
options.headless = True
options.add_argument('window-size=1920x1080') #when Headless = True

web = 'https://www.betfair.com/sport/football'
path = '/Users/frank/Downloads/chromedriver' #introduce your file's path inside '...'

#Initialize your storage
dict_frames = {}
#choosing the main european leagues
dict_countries = {
                  'german football': ['German Bundesliga', 'German Bundesliga 2'],
                  'italian football': ['Italian Serie A', 'Italian Serie B'],
                  'spanish football': ['Spanish La Liga', 'Spanish Segunda Division'],
                  'english football': ['English Premier League', 'English League 1', 'English League 2'],
                  'french football': ['French Ligue 1', 'French Ligue 2'],
                  'dutch football': ['Dutch Eredivisie'],
                  'belgian football': ['Belgian First Division A'],
                  'portuguese football': ['Portuguese Primeira Liga'],
                  'turkish football': ['Turkish Super League'],
                  'greek football': ['Greek Super League'],
}
#loop through the dictionary (we're going to open a chrome window for every element of the dictionary)
for country in dict_countries:
    for league in range(0, len(dict_countries[country])):
        try:
            # execute chromedriver with edited options
            driver = webdriver.Chrome(path, options=options)
            driver.get(web)
            driver.maximize_window() #when Headless = False
            # option1
            # accept = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="onetrust-accept-btn-handler"]')))
            # option 2
            time.sleep(2)
            accept = driver.find_element_by_xpath('//*[@id="onetrust-accept-btn-handler"]')
            accept.click()

            #set website language to English
            language_box = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'ssc-hlsw')))
            #select dropdown and then value (EN) from dropdown
            WebDriverWait(language_box, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, 'ssc-hls'))).click()
            WebDriverWait(language_box, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, 'ssc-en_GB'))).click()
            #we need to make selenium wait for the website to load after switching languages ---How?---> wait for some element to be loaded in English e.g. "Over/Under 2.5 Goals" text
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Over/Under 2.5 Goals")]')))

            #Scraping different competitions across the leagues within the dictionary
            header = driver.find_element_by_class_name('updated-competitions')
            competition = WebDriverWait(header, 5).until(EC.element_to_be_clickable((By.XPATH, './/a[contains(@title, "COMPETITIONS")]')))
            competition.click()
            competitions_table = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'mod-multipickazmenu-1061-container')))
            country_button = WebDriverWait(competitions_table, 5).until(EC.element_to_be_clickable((By.XPATH, './/div[contains(@data-category,' +'"' + country + '"' + ')]')))
            country_button.click()
            league_button = WebDriverWait(competitions_table, 5).until(EC.element_to_be_clickable((By.XPATH, './/a[contains(@data-galabel,' +'"' + dict_countries[country][league] + '"' + ')]')))
            league_button.click()

            #Choose your betting market and initialize store
            markets = ['Over/Under 2.5 Goals', 'Both teams to Score?']
            dict_odds = {}
            #scraping the betting markets we chose
            for i, market in enumerate(markets):
                dropdown = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'marketchooser-container')))
                dropdown.click()
                chooser = WebDriverWait(dropdown, 5).until(EC.element_to_be_clickable((By.XPATH, '//*[contains(text(),'+'"'+str(market)+'"'+')]')))
                chooser.click()
                #initialize storagei of data to be scraped
                list_odds = []
                teams = []
                list_dates = []
                time.sleep(1)
                #finding the sections. each section contains the matches for a specific date
                sections = driver.find_elements_by_class_name('section')
                #looping through each date
                for section in sections:
                    section_date = []
                    section_date.append(section.find_element_by_class_name('section-header-title').text)
                    #findind rows. each row represent one football match
                    rows = WebDriverWait(section, 5).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, 'event-information')))
                    for row in rows:
                        odds = row.find_element_by_xpath('.//div[contains(@class, "runner-list")]')
                        list_odds.append(odds.text)
                        teams_container = row.find_element_by_class_name('teams-container').text
                        teams.append(teams_container)
                    #storing the date of matches in each section
                    section_date = section_date * len(rows)
                    list_dates.append(section_date)
                #unpacking nested lists
                list_dates = [element for section in list_dates for element in section]
                #storing data scraped in dictionaries
                dict_odds['odds_%s' % i] = list_odds
                dict_odds['teams_%s' % i] = teams
                dict_odds['dates_%s' % i] = list_dates

            driver.quit()

            #making dataframes for each league scraped (inside the loop)
            df_over_under = pd.DataFrame({'Dates':dict_odds['dates_0'], 'Teams':dict_odds['teams_0'], 'over2.5':dict_odds['odds_0']}).set_index(['Teams', 'Dates'])
            df_btts = pd.DataFrame({'Dates':dict_odds['dates_1'], 'Teams':dict_odds['teams_1'], 'btts':dict_odds['odds_1']}).set_index(['Teams', 'Dates'])
            #concatenating the dataframes previously created for each betting market
            df_betfair = pd.concat([df_over_under, df_btts], axis=1, sort=True)
            df_betfair.reset_index(inplace=True)
            df_betfair.rename(columns={'index':'Teams'}, inplace=True)
            #transforming data
            df_betfair = df_betfair.fillna('')
            df_betfair = df_betfair.replace('SUSPENDED\n', '', regex=True)
            df_betfair = df_betfair.applymap(lambda x: x.strip() if isinstance(x, str) else x) #14.0\n

            #using time library to replace words "In-Play", "Today" and "Tomorrow" for numeric date
            df_betfair['Dates'] = df_betfair['Dates'].apply(lambda x: re.sub('In-Play', today.strftime("%A, %d %B"), x))
            df_betfair['Dates'] = df_betfair['Dates'].apply(lambda x: re.sub('Today', today.strftime("%A, %d %B"), x))
            df_betfair['Dates'] = df_betfair['Dates'].apply(lambda x: re.sub('Tomorrow', tomorrow.strftime("%A, %d %B"), x))
            df_betfair['Dates'] = df_betfair['Dates'].apply(lambda x: x.split(',')[1].strip())
            df_betfair['Dates'] = df_betfair['Dates'].apply(lambda x: datetime.datetime.strptime(year + ' ' + x, '%Y %d %B'))

            #storing dataframe of each league in dictionary
            dict_frames[dict_countries[country][league]] = df_betfair
        except:
            print(league)

end_time = time.time()
print('Total time: ' + str(round(end_time-start_time, 1)))

#save file
output = open('dict_betfair', 'wb') #saving the name of the file as dict_betfair
pickle.dump(dict_frames, output)
output.close()
