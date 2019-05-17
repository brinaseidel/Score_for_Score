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
	# NOTE!! This temporarily reads in data scraped from thegymternet. It will be updated once a score spreadsheet is published.

	# **************************
	# Load this data into the database
	# **************************


	def _create_db(self):

		# **************************
		# Read in The Gymternet's score spreadsheet
		# **************************

		# Totals
		scores = pd.read_csv("https://docs.google.com/spreadsheets/d/1213cgQJaKzzpwoO46m5ihT7F6poyhAzimpsu7VEgTWA/export?gid=0&format=csv")
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

	def handle(self, *args, **options):
		self._create_db()
