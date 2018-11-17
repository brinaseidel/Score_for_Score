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

	help = 'This reads in the current year\'s score data and loads it into the database.'


	# **************************
	# Load this data into the database
	# **************************


	def _create_db(self):

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



	def handle(self, *args, **options):
		self._create_db()



# Load gymnasts
#gymnast_df = scores[["gymnast", "country"]].drop_duplicates()
#for row in gymnast_df.itertuples(index=False):
#	if Gymnast.objects.filter(name=row.gymnast).exists() == False:
#		gymnast_instance = Gymnast.objects.create()
#		gymnast_instance.name = row.gymnast
#		print(row.country)
#		gymnast_instance.country = Country.objects.get(name=row.country)
