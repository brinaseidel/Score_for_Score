from django.core.management.base import BaseCommand
from scoredata.models import Gymnast, Country, Meet, Event, Score

import pandas as pd
import numpy as np
import math
from bs4 import BeautifulSoup
from requests import get
import regex as re 
import countrynames
import datetime

pd.options.mode.chained_assignment = None 

class Command(BaseCommand):

	help = 'This reads in the 2017, 2018, 2019 score data and loads it into the database.'


	# **************************
	# Load this data into the database
	# **************************


	def _create_db(self):

		# ****************************************************
		# ****************************************************
		# Create all event instances if they don't exist already
		# ****************************************************
		# ****************************************************

		for event in ["VT", "UB", "BB", "FX"]:
			for junior in [True, False]:
				try:
					event_test = Event.objects.get(name=event, junior=junior)
				except Event.DoesNotExist:
					event_instance = Event(name=event, junior=junior)
					event_instance.save()

		# ****************************************************
		# ****************************************************
		# 2017 scores
		# ****************************************************
		# ****************************************************

		# **************************
		# Read in The Gymternet's score spreadsheet
		# **************************

		# Totals
		
		totals = pd.read_csv("https://docs.google.com/spreadsheets/d/1fg3pFV1KGUCfUH7lHq_8UHdS0uH4O0yHHk4qtCV_QH4/export?gid=0&format=csv")
		totals.head()
		totals.columns = ["gymnast", "country", "meet_name", "vt1", "ub", "bb", "fx", "aa", "vt_avg"]
		totals.vt_avg = pd.to_numeric(totals.vt_avg, errors='coerce')
		# D scores
		dscore = pd.read_csv("https://docs.google.com/spreadsheets/d/1fg3pFV1KGUCfUH7lHq_8UHdS0uH4O0yHHk4qtCV_QH4/export?gid=1144828878&format=csv")
		dscore.head()
		dscore.columns = ["gymnast", "country", "meet_name", "vt1_d", "ub_d", "bb_d", "fx_d", "vt_total_d"]


		# **************************
		# Clean the scores data
		# **************************

		# Get Vault 2 scores from Vault 1 and Vault Average
		totals["vt2"] = totals.vt_avg * 2 - totals.vt1

		# Get Vault 2 d score from Vault 1 d score and total
		dscore["vt2_d"] = dscore.vt_total_d - dscore.vt1_d

		# Change some meet names for merging
		dscore.meet_name.replace("Brestyan's Qualifier", "Brestyan's National Qualifier", inplace=True)

		# Merge totals and d scores
		scores = pd.merge(totals, dscore, how="outer", on=["gymnast", "meet_name"], indicator=True)
		scores._merge.value_counts()
		# Check cases that didn't merge - where we have d scores but no totals
		print(scores.loc[scores._merge == "right_only", ["gymnast", "meet_name", "_merge"]])
		print(scores.loc[scores._merge == "right_only", ].meet_name.value_counts())
		# Delete these cases
		scores = scores.loc[scores._merge != "right_only", scores.columns[:-1]]
		# Drop country names from the D score sheet
		scores["country_x"] = np.where(scores.country_x=="", scores.country_y, scores.country_x)
		scores.drop(["country_y"], axis=1)
		scores=scores.rename(columns = {'country_x':'country'})
		# Drop vault averages and totals
		scores.drop(["vt_total_d", "vt_avg"], axis=1)

		# Clean historic data
		scores["gymnast"] = scores.gymnast.str.replace("De Jesus dos Santos", "de Jesus dos Santos")
		scores["gymnast"] = scores.gymnast.str.replace("De Jesus Dos Santos", "de Jesus dos Santos")
		scores["gymnast"] = scores.gymnast.str.replace("Laurie Denommee", "Laurie Dénommée")

		# **************************
		# Clean the meet type
		# **************************
		scores["meet_day"] = ""
		day_types = ["QF", "TF", "AA", "EF"]
		for day in day_types:
			scores["meet_day"] = np.where(scores.meet_name.str.contains(day), day, scores.meet_day)
		scores.meet_day.value_counts()
		# Clean meet names to remove the type
		for day in day_types:
			scores["meet_name"] = scores.meet_name.str.replace(day, "")

		scores["meet_name"] = scores.meet_name.str.replace("Champs", "Championships")
		scores["meet_name"] = scores.meet_name.str.replace("FIT", "Flanders International Team")
		scores["meet_name"] = scores.meet_name.str.replace("Euros", "European Championships")
		scores["meet_name"] = scores.meet_name.str.replace("Euro Youth Olympic Festival", "European Youth Olympic Festival")
		scores["meet_name"] = scores.meet_name.str.replace("Gymnix", "International Gymnix")
		scores["meet_name"] = scores.meet_name.str.replace("Universiade", "Summer Universiade")
		scores["meet_name"] = scores.meet_name.str.replace("Jesolo", "City of Jesolo Trophy")
		scores["meet_name"] = scores.meet_name.str.replace("Top Gym", "Top Gym Tournament")
		scores["meet_name"] = scores.meet_name.str.replace("DTB Pokal", "DTB Pokal Team Challenge")
		scores["meet_name"] = scores.meet_name.str.replace("Gymnova", "Gymnova Cup")
		scores["meet_name"] = scores.meet_name.str.replace("Unni & Haralds", "Unni & Haralds Trophy")
		scores["meet_name"] = scores.meet_name.str.replace("Hungarian Masters", "Hungarian Master Championships")
		scores["meet_name"] = scores.meet_name.str.replace("Austrian Open", "Austrian Team Open")
		scores["meet_name"] = scores.meet_name.str.replace("2nd Norwegian FIG", "2nd Norwegian FIG Meet")
		scores["meet_name"] = scores.meet_name.str.replace("Brestyan's National Qualifier", "Brestyan’s National Qualifier")
		scores["meet_name"] = scores.meet_name.str.replace("Mediterranean", "Mediterranean Junior Championships")
		scores["meet_name"] = scores.meet_name.str.replace("Stella Zakharova", "Stella Zakharova Cup")
		scores["meet_name"] = scores.meet_name.str.replace("Pan Am Championships", "Pan American Championships")
		scores["meet_name"] = scores.meet_name.str.replace("Reykjavik International", "Reykjavik International Games")
		scores["meet_name"] = scores.meet_name.str.replace("Dutch Invitational", "Dutch Women’s Invitational")
		scores["meet_name"] = scores.meet_name.str.replace("Junior Japan", "Junior Japan International")
		for city in ["Melbourne", "Baku", "Cottbus",  "Doha"]:
			scores["meet_name"] = scores.meet_name.str.replace(city, city + " World Cup")
		for city in ["Paris", "Osijek", "Koper", "Szombathely", "Varna"]:
			scores["meet_name"] = scores.meet_name.str.replace(city, city + " Challenge Cup")
		for meet in ["South American Junior", "France Top 12"]:
			scores["meet_name"] = scores.meet_name.str.replace(meet, meet + " Championships")
		# **************************
		# Mark juniors
		# **************************
		scores["junior2017"] = False
		scores["junior2017"] = np.where(scores.gymnast.str.contains("\*"), True, scores.junior2017)
		scores["gymnast"] = scores.gymnast.str.replace("\*", "")

		# **************************
		# Get meet start and end dates
		# **************************

		# Download the HTML from TheGymternet's list of meets
		response = get("https://thegymter.net/2017-gymnastics-calendar/")
		soup = BeautifulSoup(response.text, 'html.parser')
		meets = soup.find("table").findAll("tr")

		# Set up arrays to store the meet data
		start_date=[]
		end_date=[]
		meet_name=[]
		meet_loc=[]

		# Definte a regular expression to get alphabetic characters from a string - we will use this to spearate months from days
		regex = re.compile('[^a-zA-Z]')

		# Loop through the meets (skipping the first row which has headings)
		for meet in meets[1:]:
			
			# Clean start and end date 
			date = meet.findAll("td")[0].text
			date = date.split("-")
			start_date.append(date[0] + " 2017")
			# Cases where the meet is only one day
			if len(date) == 1:
				end_date.append(date[0] + " 2017")
			# Cases where the meet is many days, but the dates are in the same month
			elif regex.sub('', date[1]) == "":
				month = regex.sub('', date[0])
				end_date.append(month + " " + date[1] + " 2017")
			# Cases where the meet is many days, but they dates are in different months
			else:
				end_date.append(date[1] + " 2017")
			# Clean month formats


			# Pull meet name
			meet_name.append(meet.findAll("td")[1].find("a").contents[0])

			# Pull meet location
			meet_loc_try = meet.findAll("td")[1].text.split(",", maxsplit=1)
			if len(meet_loc_try) > 1:
				meet_loc.append(meet_loc_try[1])
			else:
				meet_loc.append("")
				
		# Combine results in data frame
		meets = pd.DataFrame({
				'meet_name': meet_name,
				'start_date': start_date, 
				'end_date': end_date,
				'meet_loc': meet_loc})

		# Clean some dates
		meets.start_date = meets.start_date.str.replace("June", "Jun")
		meets.start_date = meets.start_date.str.replace("July", "Jul")
		meets.end_date = meets.end_date.str.replace("July", "Jul")
		meets.end_date = meets.end_date.str.replace("June", "Jun")

		# Merge in the meets
		scores["meet_name"] = scores.meet_name.str.strip()
		meets["meet_name"] = meets.meet_name.str.strip()
		scores = pd.merge(scores, meets, how="outer", on=["meet_name"], indicator=True)
		print(scores._merge.value_counts())
		# Check cases that didn't merge - not that many. Fine for now.
		scores = scores.loc[scores._merge != "right_only", scores.columns[:-1]]

		scores['meet_name'] = scores['meet_name'].astype(str) + " (2017)"

		# **************************
		# Load countries in
		# **************************

		# Clean some countries with typoes
		scores.country.replace("Chia", "China", inplace=True)

		# Load countries in
		countries_df = scores.country.drop_duplicates()
		for country in countries_df:
			try:
				country_test = Country.objects.get(name=country)
			except Country.DoesNotExist:
				if country != "Chinese Taipei" and country != "Taiwan":
					country_instance = Country(name = country, iso3c = countrynames.to_code_3(country))
					country_instance.save()
				else:
					try:
						country_test = Country.objects.get(name="Taiwan")
					except Country.DoesNotExist:
						country_instance = Country(name = "Taiwan", iso3c = "TWN")
						country_instance.save()

		# **************************
		# Load meets in 
		# **************************

		meets_df = scores[["meet_name", "start_date", "end_date", "meet_loc"]].drop_duplicates()
		meets_df["start_date_fmt"] = pd.to_datetime(meets_df.start_date, format="%b %d %Y")
		meets_df["end_date_fmt"] = pd.to_datetime(meets_df.end_date, format="%b %d %Y")
		for meet in meets_df.itertuples():
			try:
				meet_test = Meet.objects.get(name=meet.meet_name)
			except Meet.DoesNotExist:
				if pd.isnull(meet.start_date_fmt)==False:
					meet_instance = Meet(name = meet.meet_name, start_date=meet.start_date_fmt, end_date = meet.end_date_fmt)
				else:
					meet_instance = Meet(name = meet.meet_name)
				meet_instance.save()
				print(meet_instance)

		# **************************
		# Load gymnasts in 
		# **************************

		gymnasts_df = scores[["gymnast", "country"]].drop_duplicates()
		gymnasts_df.country.replace("Chinese Taipei", "Taiwan", inplace=True)
		for person in gymnasts_df.itertuples():
			try:
				gymnast_test = Gymnast.objects.get(name=person.gymnast)
			except Gymnast.DoesNotExist:
				gymnast_instance = Gymnast(name = person.gymnast, country = Country.objects.get(name=person.country))
				gymnast_instance.save()
		
		# **************************
		# Load scores in 
		# **************************

		for row in scores.itertuples():
			score_test = Score.objects.filter(gymnast=Gymnast.objects.get(name=row.gymnast), meet=Meet.objects.get(name=row.meet_name), meet_day=row.meet_day)
			if score_test.count() == 0:
				# Vault 1
				if pd.isnull(row.vt1)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="VT", junior=row.junior2017), score=row.vt1, d_score=row.vt1_d, score_num=1)
					score_instance.save()
				# Bars
				if pd.isnull(row.ub)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="UB", junior=row.junior2017), score=row.ub, d_score=row.ub_d, score_num=1)
					score_instance.save()
				# Balance beam
				if pd.isnull(row.bb)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="BB", junior=row.junior2017), score=row.bb, d_score=row.bb_d, score_num=1)
					score_instance.save()
				# Floor
				if pd.isnull(row.fx)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="FX", junior=row.junior2017), score=row.fx, d_score=row.fx_d, score_num=1)
					score_instance.save()
				# Vault 2
				if pd.isnull(row.vt2)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="VT", junior=row.junior2017), score=row.vt2, d_score=row.vt2_d, score_num=2)
					score_instance.save()

		# **************************
		# Add dates for some meets without dates
		# **************************
		for meet_name in ["Elite Gym Massilia Masters (2017)", "Elite Gym Massilia Open (2017)", "Elite Gym Massila Espoir (2017)"]:
			meet = Meet.objects.get(name = meet_name)
			meet.start_date = datetime.date(2017, 11, 17)
			meet.end_date = datetime.date(2017, 11, 19)
			meet.save()
		meet = Meet.objects.get(name = "Czech European Championships Test (2017)")
		meet.start_date = datetime.date(2017, 3, 18)
		meet.save()
		meet = Meet.objects.get(name = "Brazilian Selection (2017)")
		meet.start_date = datetime.date(2017, 7, 22)
		meet.end_date = datetime.date(2017, 7, 24)
		meet.save()
		meet = Meet.objects.get(name = "Stuttgart World Cup (2017)")
		meet.start_date = datetime.date(2017, 3, 18)
		meet.end_date = datetime.date(2017, 3, 19)
		meet.save()
		meet = Meet.objects.get(name = "France Top 12 Championships (2017)")
		meet.start_date = datetime.date(2017, 3, 11)
		meet.end_date = datetime.date(2017, 3, 12)
		meet.save()
		meet = Meet.objects.get(name = "German Junior Friendly (2017)")
		meet.start_date = datetime.date(2017, 7, 8)
		meet.save()

		# ****************************************************
		# ****************************************************
		# 2018 scores
		# ****************************************************
		# ****************************************************

		# **************************
		# Read in The Gymternet's score spreadsheet
		# **************************

		# Totals
		totals = pd.read_csv("https://docs.google.com/spreadsheets/d/1HI0tOSgjIS8rFjbTwCTlhG1LxP6sttzDMN3-4u0B0u4/export?gid=0&format=csv")
		totals.head()
		totals.columns = ["gymnast", "country", "meet_name", "vt1", "ub", "bb", "fx", "aa", "vt_avg"]

		# D scores
		dscore = pd.read_csv("https://docs.google.com/spreadsheets/d/1HI0tOSgjIS8rFjbTwCTlhG1LxP6sttzDMN3-4u0B0u4/export?gid=1212101599&format=csv")
		dscore.head()
		#dscore.drop(dscore.columns[len(dscore.columns)-1], axis=1, inplace=True)
		dscore.columns = ["gymnast", "country", "meet_name", "vt1_d", "ub_d", "bb_d", "fx_d", "vt_total_d"]


		# **************************
		# Clean the scores data
		# **************************

		# Get Vault 2 scores from Vault 1 and Vault Average
		totals["vt2"] = totals.vt_avg * 2 - totals.vt1

		# Get Vault 2 d score from Vault 1 d score and total
		dscore["vt2_d"] = dscore.vt_total_d - dscore.vt1_d

		# Merge totals and d scores
		scores = pd.merge(totals, dscore, how="outer", on=["gymnast", "meet_name"], indicator=True)
		scores._merge.value_counts()
		# Check cases that didn't merge - where we have d scores but no totals
		scores.loc[scores._merge == "right_only", ["gymnast", "meet_name", "_merge"]]
		scores.loc[scores._merge == "right_only", ].meet_name.value_counts()
		# Delete these cases
		scores = scores.loc[scores._merge != "right_only", scores.columns[:-1]]
		# Drop country names from the D score sheet
		scores["country_x"] = np.where(scores.country_x=="", scores.country_y, scores.country_x)
		scores.drop(["country_y"], axis=1)
		scores=scores.rename(columns = {'country_x':'country'})
		# Drop vault averages and totals
		scores.drop(["vt_total_d", "vt_avg"], axis=1)

		# Clean some typos
		try:
			scores["ub_d"] = scores.ub_d.str.replace(".4.3", "4.3")
		except:
			print("I guess the score typo was fixed...")
		scores["gymnast"] = scores.gymnast.str.replace("De Jesus dos Santos", "de Jesus dos Santos")
		scores["gymnast"] = scores.gymnast.str.replace("De Jesus Dos Santos", "de Jesus dos Santos")
		scores["gymnast"] = scores.gymnast.str.replace("Laurie Denommee", "Laurie Dénommée")

		# **************************
		# Clean the meet type
		# **************************
		scores["meet_day"] = ""
		day_types = ["QF", "TF", "AA", "EF"]
		for day in day_types:
			scores["meet_day"] = np.where(scores.meet_name.str.contains(day), day, scores.meet_day)
		scores.meet_day.value_counts()
		# Clean meet names to remove the type
		for day in day_types:
			scores["meet_name"] = scores.meet_name.str.replace(day, "")

		# **************************
		# Mark juniors
		# **************************
		scores["junior2018"] = False
		scores["junior2018"] = np.where(scores.gymnast.str.contains("\*"), True, scores.junior2018)
		scores["gymnast"] = scores.gymnast.str.replace("\*", "")

		# **************************
		# Get meet start and end dates
		# **************************

		# Download the HTML from TheGymternet's list of meets
		response = get("https://thegymter.net/2018-gymnastics-calendar/")
		soup = BeautifulSoup(response.text, 'html.parser')
		meets = soup.find("table").findAll("tr")

		# Set up arrays to store the meet data
		start_date=[]
		end_date=[]
		meet_name=[]
		meet_loc=[]

		# Definte a regular expression to get alphabetic characters from a string - we will use this to spearate months from days
		regex = re.compile('[^a-zA-Z]')

		# Loop through the meets (skipping the first row which has headings)
		for meet in meets:
			
			# Clean start and end date 
			date = meet.findAll("td")[0].text
			date = date.split("-")
			start_date.append(date[0] + " 2018")
			# Cases where the meet is only one day
			if len(date) == 1:
				end_date.append(date[0] + " 2018")
			# Cases where the meet is many days, but the dates are in the same month
			elif regex.sub('', date[1]) == "":
				month = regex.sub('', date[0])
				end_date.append(month + " " + date[1] + " 2018")
			# Cases where the meet is many days, but they dates are in different months
			else:
				end_date.append(date[1] + " 2018")
				
			# Pull meet name
			meet_name.append(meet.findAll("td")[1].text)
			
			# Pull meet location
			meet_loc.append(meet.findAll("td")[2].text)
				
		# Combine results in data frame
		meets = pd.DataFrame({
				'meet_name': meet_name,
				'start_date': start_date, 
				'end_date': end_date,
				'meet_loc': meet_loc})

		# Drop MAG meets
		meets = meets.loc[~meets.meet_name.str.contains("MAG"), :]

		# Merge in the meets
		scores["meet_name"] = scores.meet_name.str.strip()
		meets["meet_name"] = meets.meet_name.str.strip()
		scores = pd.merge(scores, meets, how="outer", on=["meet_name"], indicator=True)
		scores._merge.value_counts()
		# Check cases that didn't merge - not that many. Fine for now.
		scores = scores.loc[scores._merge != "right_only", scores.columns[:-1]]

		# Add the year to the meet name (because some meets occur every year)
		scores['meet_name'] = scores['meet_name'].astype(str) + " (2018)"
		# **************************
		# Load countries in
		# **************************

		countries_df = scores.country.drop_duplicates()
		for country in countries_df:
			try:
				country_test = Country.objects.get(name=country)
			except Country.DoesNotExist:
				if country != "Chinese Taipei" and country != "Taiwan":
					country_instance = Country(name = country, iso3c = countrynames.to_code_3(country))
					country_instance.save()
				else:
					try:
						country_test = Country.objects.get(name="Taiwan")
					except Country.DoesNotExist:
						country_instance = Country(name = "Taiwan", iso3c = "TWN")
						country_instance.save()

		# **************************
		# Load meets in 
		# **************************

		meets_df = scores[["meet_name", "start_date", "end_date", "meet_loc"]].drop_duplicates()
		meets_df["start_date_fmt"] = pd.to_datetime(meets_df.start_date, format="%b %d %Y")
		meets_df["end_date_fmt"] = pd.to_datetime(meets_df.end_date, format="%b %d %Y")
		for meet in meets_df.itertuples():
			try:
				meet_test = Meet.objects.get(name=meet.meet_name)
			except Meet.DoesNotExist:
				if pd.isnull(meet.start_date_fmt)==False:
					meet_instance = Meet(name = meet.meet_name, start_date=meet.start_date_fmt, end_date = meet.end_date_fmt)
				else:
					meet_instance = Meet(name = meet.meet_name)
				meet_instance.save()
				print(meet_instance)

		# **************************
		# Load gymnasts in 
		# **************************

		gymnasts_df = scores[["gymnast", "country"]].drop_duplicates()
		gymnasts_df.country.replace("Chinese Taipei", "Taiwan", inplace=True)
		for person in gymnasts_df.itertuples():
			try:
				gymnast_test = Gymnast.objects.get(name=person.gymnast)
			except Gymnast.DoesNotExist:
				gymnast_instance = Gymnast(name = person.gymnast, country = Country.objects.get(name=person.country))
				gymnast_instance.save()
		
		# **************************
		# Load scores in 
		# **************************

		for row in scores.itertuples():
			score_test = Score.objects.filter(gymnast=Gymnast.objects.get(name=row.gymnast), meet=Meet.objects.get(name=row.meet_name), meet_day=row.meet_day)
			if score_test.count() == 0:
				# Vault 1
				if pd.isnull(row.vt1)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="VT", junior=row.junior2018), score=row.vt1, d_score=row.vt1_d, score_num=1)
					score_instance.save()
				# Bars
				if pd.isnull(row.ub)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="UB", junior=row.junior2018), score=row.ub, d_score=row.ub_d, score_num=1)
					score_instance.save()
				# Balance beam
				if pd.isnull(row.bb)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="BB", junior=row.junior2018), score=row.bb, d_score=row.bb_d, score_num=1)
					score_instance.save()
				# Floor
				if pd.isnull(row.fx)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="FX", junior=row.junior2018), score=row.fx, d_score=row.fx_d, score_num=1)
					score_instance.save()
				# Vault 2
				if pd.isnull(row.vt2)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="VT", junior=row.junior2018), score=row.vt2, d_score=row.vt2_d, score_num=2)
					score_instance.save()

		# **************************
		# Add dates for some meets without dates
		# **************************
		meet = Meet.objects.get(name = "U.S. Verification (April) (2018)")
		meet.start_date = datetime.date(2018, 4, 8)
		meet.end_date = datetime.date(2018, 4, 8)		
		meet.save()
		meet = Meet.objects.get(name = "Top 12 Final (2018)")
		meet.start_date = datetime.date(2018, 3, 17)
		meet.end_date = datetime.date(2018, 3, 17)
		meet.save()
		meet = Meet.objects.get(name = "Brestyan's National Qualifier (2018)")
		meet.start_date = datetime.date(2018, 6, 23)
		meet.end_date = datetime.date(2018, 6, 24)
		meet.save()
		meet = Meet.objects.get(name = "Desert Lights Qualifier (2018)")
		meet.start_date = datetime.date(2018, 1, 27)
		meet.end_date = datetime.date(2018, 1, 28)
		meet.save()
		meet = Meet.objects.get(name = "Orlando Qualifier (2018)")
		meet.start_date = datetime.date(2018, 2, 9)
		meet.end_date = datetime.date(2018, 2, 11)
		meet.save()
		meet = Meet.objects.get(name = "President's Cup (2018)")
		meet.start_date = datetime.date(2018, 2, 12)
		meet.end_date = datetime.date(2018, 2, 16)
		meet.save()
		meet = Meet.objects.get(name = "Klaverblad Championships (2018)")
		meet.start_date = datetime.date(2018, 6, 9)
		meet.end_date = datetime.date(2018, 6, 10)
		meet.save()
		meet = Meet.objects.get(name = "Buckeye Qualifier (2018)")
		meet.start_date = datetime.date(2018, 2, 1)
		meet.end_date = datetime.date(2018, 2, 2)
		meet.save()
		meet = Meet.objects.get(name = "Swiss Duel (2018)")
		meet.start_date = datetime.date(2018, 9, 23)
		meet.end_date = datetime.date(2018, 9, 23)
		meet.save()
		meet = Meet.objects.get(name = "German Worlds Trial (2018)")
		meet.start_date = datetime.date(2018, 9, 15)
		meet.end_date = datetime.date(2018, 9, 15)
		meet.save()

		# ****************************************************
		# ****************************************************
		# 2019 scores
		# ****************************************************
		# ****************************************************

		# **************************
		# Read in The Gymternet's score spreadsheet
		# **************************

		# Totals
		scores = pd.read_csv("https://docs.google.com/spreadsheets/d/1213cgQJaKzzpwoO46m5ihT7F6poyhAzimpsu7VEgTWA/export?gid=1358682386&format=csv")
		scores.head()
		scores.columns = ["gymnast", "country", "meet_name", "meet_day", "vt1", "vt2", "ub", "bb", "fx", "vt1_d", "vt2_d", "ub_d", "bb_d", "fx_d", "meet_loc", "start_date", "end_date", "junior2019"]

		# **************************
		# Clean the scores data
		# **************************

		# **************************
		# Clean the meet type
		# **************************

		# **************************
		# Mark juniors
		# **************************
		scores["junior2019"] = (scores["junior2019"] == True)

		# **************************
		# Get meet start and end dates
		# **************************

		# Add the year to the meet name (because some meets occur every year)
		scores['meet_name'] = scores['meet_name'].astype(str) + " (2019)"

		# **************************
		# Load countries in
		# **************************

		countries_df = scores.country.drop_duplicates()
		for country in countries_df:
			try:
				country_test = Country.objects.get(name=country)
			except Country.DoesNotExist:
				if country != "Chinese Taipei" and country != "Taiwan":
					country_instance = Country(name = country, iso3c = countrynames.to_code_3(country))
					country_instance.save()
				else:
					try:
						country_test = Country.objects.get(name="Taiwan")
					except Country.DoesNotExist:
						country_instance = Country(name = "Taiwan", iso3c = "TWN")
						country_instance.save()

		# **************************
		# Load meets in 
		# **************************

		meets_df = scores[["meet_name", "start_date", "end_date", "meet_loc"]].drop_duplicates()
		meets_df["start_date_fmt"] = pd.to_datetime(meets_df.start_date, format="%b %d %Y")
		meets_df["end_date_fmt"] = pd.to_datetime(meets_df.end_date, format="%b %d %Y")
		for meet in meets_df.itertuples():
			try:
				meet_test = Meet.objects.get(name=meet.meet_name)
			except Meet.DoesNotExist:
				if pd.isnull(meet.start_date_fmt)==False:
					meet_instance = Meet(name = meet.meet_name, start_date=meet.start_date_fmt, end_date = meet.end_date_fmt)
				else:
					meet_instance = Meet(name = meet.meet_name)
				meet_instance.save()
				print(meet_instance)

		# **************************
		# Load gymnasts in 
		# **************************

		gymnasts_df = scores[["gymnast", "country"]].drop_duplicates()
		gymnasts_df.country.replace("Chinese Taipei", "Taiwan", inplace=True)
		for person in gymnasts_df.itertuples():
			try:
				gymnast_test = Gymnast.objects.get(name=person.gymnast)
			except Gymnast.DoesNotExist:
				gymnast_instance = Gymnast(name = person.gymnast, country = Country.objects.get(name=person.country))
				gymnast_instance.save()
		
		# **************************
		# Load scores in 
		# **************************

		for row in scores.itertuples():
			score_test = Score.objects.filter(gymnast=Gymnast.objects.get(name=row.gymnast), meet=Meet.objects.get(name=row.meet_name), meet_day=row.meet_day)
			if score_test.count() == 0:
				# Vault 1
				if pd.isnull(row.vt1)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="VT", junior=row.junior2019), score=row.vt1, d_score=row.vt1_d, score_num=1)
					score_instance.save()
				# Bars
				if pd.isnull(row.ub)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="UB", junior=row.junior2019), score=row.ub, d_score=row.ub_d, score_num=1)
					score_instance.save()
				# Balance beam
				if pd.isnull(row.bb)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="BB", junior=row.junior2019), score=row.bb, d_score=row.bb_d, score_num=1)
					score_instance.save()
				# Floor
				if pd.isnull(row.fx)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="FX", junior=row.junior2019), score=row.fx, d_score=row.fx_d, score_num=1)
					score_instance.save()
				# Vault 2
				if pd.isnull(row.vt2)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="VT", junior=row.junior2019), score=row.vt2, d_score=row.vt2_d, score_num=2)
					score_instance.save()

		# ****************************************************
		# ****************************************************
		# 2020 scores
		# ****************************************************
		# ****************************************************

				# **************************
		# Read in The Gymternet's score spreadsheet
		# **************************

		# Totals
		#scores = pd.read_csv("https://docs.google.com/spreadsheets/d/1mAZlBhTIPOSZND4Z90ZmHJgobSqU8jv5dGpl54DHWSw/export?gid=0&format=csv") # used to need gid=0, now it causes 400 error
		scores = pd.read_csv("https://docs.google.com/spreadsheets/d/1mAZlBhTIPOSZND4Z90ZmHJgobSqU8jv5dGpl54DHWSw/export?format=csv")
		scores.head()
		scores.columns = ["gymnast", "country", "meet_name", "meet_day", "vt1", "vt2", "ub", "bb", "fx", "vt1_d", "vt2_d", "ub_d", "bb_d", "fx_d", "meet_loc", "start_date", "end_date", "junior2020"]

		# **************************
		# Clean the scores data
		# **************************

		# **************************
		# Clean the meet type
		# **************************

		# **************************
		# Mark juniors
		# **************************
		scores["junior2020"] = (scores["junior2020"] == True)

		# **************************
		# Get meet start and end dates
		# **************************

		# Add the year to the meet name (because some meets occur every year)
		scores['meet_name'] = scores['meet_name'].astype(str) + " (2020)"

		# **************************
		# Load countries in
		# **************************

		countries_df = scores.country.drop_duplicates()
		for country in countries_df:
			try:
				country_test = Country.objects.get(name=country)
			except Country.DoesNotExist:
				if country != "Chinese Taipei" and country != "Taiwan":
					country_instance = Country(name = country, iso3c = countrynames.to_code_3(country))
					country_instance.save()
				else:
					try:
						country_test = Country.objects.get(name="Taiwan")
					except Country.DoesNotExist:
						country_instance = Country(name = "Taiwan", iso3c = "TWN")
						country_instance.save()

		# **************************
		# Load meets in 
		# **************************

		meets_df = scores[["meet_name", "start_date", "end_date", "meet_loc"]].drop_duplicates()
		meets_df["start_date_fmt"] = pd.to_datetime(meets_df.start_date, format="%b %d %Y")
		meets_df["end_date_fmt"] = pd.to_datetime(meets_df.end_date, format="%b %d %Y")
		for meet in meets_df.itertuples():
			try:
				meet_test = Meet.objects.get(name=meet.meet_name)
			except Meet.DoesNotExist:
				if pd.isnull(meet.start_date_fmt)==False:
					meet_instance = Meet(name = meet.meet_name, start_date=meet.start_date_fmt, end_date = meet.end_date_fmt)
				else:
					meet_instance = Meet(name = meet.meet_name)
				meet_instance.save()
				print(meet_instance)

		# **************************
		# Load gymnasts in 
		# **************************

		gymnasts_df = scores[["gymnast", "country"]].drop_duplicates()
		gymnasts_df.country.replace("Chinese Taipei", "Taiwan", inplace=True)
		for person in gymnasts_df.itertuples():
			try:
				gymnast_test = Gymnast.objects.get(name=person.gymnast)
			except Gymnast.DoesNotExist:
				gymnast_instance = Gymnast(name = person.gymnast, country = Country.objects.get(name=person.country))
				gymnast_instance.save()
		
		# **************************
		# Load scores in 
		# **************************

		for row in scores.itertuples():
			score_test = Score.objects.filter(gymnast=Gymnast.objects.get(name=row.gymnast), meet=Meet.objects.get(name=row.meet_name), meet_day=row.meet_day)
			if score_test.count() == 0:
				# Vault 1
				if pd.isnull(row.vt1)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="VT", junior=row.junior2020), score=row.vt1, d_score=row.vt1_d, score_num=1)
					score_instance.save()
				# Bars
				if pd.isnull(row.ub)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="UB", junior=row.junior2020), score=row.ub, d_score=row.ub_d, score_num=1)
					score_instance.save()
				# Balance beam
				if pd.isnull(row.bb)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="BB", junior=row.junior2020), score=row.bb, d_score=row.bb_d, score_num=1)
					score_instance.save()
				# Floor
				if pd.isnull(row.fx)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="FX", junior=row.junior2020), score=row.fx, d_score=row.fx_d, score_num=1)
					score_instance.save()
				# Vault 2
				if pd.isnull(row.vt2)==False:
					score_instance = Score(gymnast = Gymnast.objects.get(name=row.gymnast), 
						meet = Meet.objects.get(name=row.meet_name),
						meet_day = row.meet_day, event=Event.objects.get(name="VT", junior=row.junior2020), score=row.vt2, d_score=row.vt2_d, score_num=2)
					score_instance.save()

	def handle(self, *args, **options):
		self._create_db()
