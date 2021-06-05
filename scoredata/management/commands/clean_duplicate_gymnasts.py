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

	help = 'This combines records for gymnasts with multiple records for similar versions of their name.'

	


	def _clean_dups(self):

		# **************************
		# Cases where one version has iia and the other has ia
		# **************************
		gymnasts_to_clean = Gymnast.objects.filter(name__contains='iia ')
		for gymnast in gymnasts_to_clean:

			# Get name of duplicate gymnast
			duplicate_name = gymnast.name.replace('iia ', 'ia ')

			try:
				# Find the duplicate gymnast object
				duplicate_gymnast = Gymnast.objects.get(name=duplicate_name)
				print("Combining {} and {}".format(gymnast.name, duplicate_name))
				# Add all scores from the 'iia' copy to the 'ia' copy
				scores = gymnast.score_set.all()
				scores.update(gymnast=duplicate_gymnast)
				# Remove duplicate
				gymnast.delete()

			except Gymnast.DoesNotExist:
				pass

		# **************************
		# Cases where one version has é and the other has e
		# **************************
		gymnasts_to_clean = Gymnast.objects.filter(name__contains='é')
		for gymnast in gymnasts_to_clean:

			# Get name of duplicate gymnast
			duplicate_name = gymnast.name.replace('é', 'e')

			try:
				# Find the duplicate gymnast object
				duplicate_gymnast = Gymnast.objects.get(name=duplicate_name)
				print("Combining {} and {}".format(gymnast.name, duplicate_name))
				# Add all scores from the 'iia' copy to the 'ia' copy
				scores = gymnast.score_set.all()
				scores.update(gymnast=duplicate_gymnast)
				# Remove duplicate
				gymnast.delete()

			except Gymnast.DoesNotExist:
				pass

                try:
                        gymnast = Gymnast.objects.get(name="Jade Carey ")
                        duplicate_gymnast = Gymnast.objects.get(name="Jade Carey")
                        scores = gymnast.score_set.all()
                        scores.update(gymnast=duplicate_gymnast)
                        gymnast.delete()
                except Gymnast.DoesNotExist:
                        pass

                try:
                        gymnast = Gymnast.objects.get(name="Morgan Jewel")
                        duplicate_gymnast = Gymnast.objects.get(name="Morgan Jewell")
                        scores = gymnast.score_set.all()
                        scores.update(gymnast=duplicate_gymnast)
                        gymnast.delete()
                except Gymnast.DoesNotExist:
                        pass

                

	def handle(self, *args, **options):
		self._clean_dups()
