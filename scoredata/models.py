from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
import uuid
from datetime import datetime	
import pandas as pd
import os
from django.template.defaultfilters import slugify

# **************************
# Score database models
# **************************

# Model for each gymnast
class Gymnast(models.Model):

	name = models.CharField(max_length=200, help_text="Enter a gymnast's name")
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, help_text="Unique ID for this particular gymnast across whole database")
	country = models.ForeignKey('Country', null=True, on_delete=models.SET_NULL)
	# For birth year, we can't make a DateField that just stores the year so we'll make it an integer and set a min and a max
	#year_of_birth = models.PositiveIntegerField(validators=[MinValueValidator(1950), MaxValueValidator(datetime.now().year)], help_text="Use the following format: <YYYY>", null=True)
	summary = models.TextField(max_length=1000, help_text='Enter a brief description of the gymnats', null=True)

	def __str__(self):
		"""
		String for representing the Model object (in Admin site etc.)
		"""
		return self.name

	def get_absolute_url(self):
		"""
		Returns the url to access a detail record for this gymnast.
		"""
		return reverse('gymnast-detail', args=[str(self.id)])


class Country(models.Model):

	name = models.CharField(max_length=200, help_text="Country name")
	iso3c = models.CharField(max_length=3, help_text = "Country ISO3c code")

	class Meta:
		verbose_name_plural = "Countries"
		ordering = ["name"]

	def __str__(self):
		return self.name

# Model for each meet
class Meet(models.Model):

	name = models.CharField(max_length=250, help_text = "Enter the name of the meet")
	start_date = models.DateField(null=True, blank=True)
	end_date = models.DateField(null=True, blank=True)
	gymnast = models.ManyToManyField(Gymnast, help_text='Gymnasts who competed at this meet')
	id = models.AutoField(primary_key=True)

	def __str__(self):
		return self.name

	def get_absolute_url(self):
		return reverse('meet-detail', args=[str(self.id)])

	class Meta:
		ordering = ["-start_date"]


# Model for which event (VT, UB, BB, FX)
class Event(models.Model):

	event_names = (
		('VT', 'Valult'),
		('UB', 'Uneven Bars'),
		('BB', 'Balance Beam'),
		('FX', 'Floor Exercise'),
	)
	name = models.CharField(max_length = 2, choices = event_names, help_text = "Event")
	junior = models.BooleanField(default=False)

	def __str__(self):
		return self.name

# Model for a gymnast's scores on a given day of a given meet
class Score(models.Model):
	meet = models.ForeignKey(Meet, on_delete=models.CASCADE)
	meet_day_opts = (
		("QF", "Qualifying"),
		("TF", "Team Final"), 
		("AA", "All Around Final"),
		("EF", "Event Finals"),
	)
	meet_day = models.CharField(max_length=5, choices=meet_day_opts, blank=True, help_text='Day of the meet')
	gymnast = models.ForeignKey(Gymnast, on_delete=models.CASCADE)
	event = models.ForeignKey(Event, on_delete=models.CASCADE)
	score = models.FloatField(help_text = "Total Score", null=True)
	d_score = models.FloatField(help_text = "Difficulty Score", null=True)
	# Add a score num field so that we can record first vault vs second vaults
	score_num = models.PositiveIntegerField(default=1)

	def __str__(self):
		return str(self.score)

# **************************
# Blog models
# **************************

class Author(models.Model):
	first_name  = models.CharField(max_length=100, null=True)
	last_name = models.CharField(max_length=100, null=True)
	slug = models.SlugField(max_length=130, null=True, blank=True)

	def __str__(self):
		return "{} {}".format(self.first_name, self.last_name)

	def save(self, *args, **kwargs):
		if not self.id:
			# Newly created object, so set slug
			self.slug = slugify(self.first_name + " " + self.last_name)

		super(Author, self).save(*args, **kwargs)

	def get_absolute_url(self):
		"""
		Returns the url to access a detail record for this gymnast.
		"""
		return reverse("author-detail", kwargs={"slug": self.slug})

class Post(models.Model):
	author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True)
	title = models.CharField(max_length=500)
	text = models.TextField(help_text="Text of the blog post goes here")
	date = models.DateField()
	tag = models.ManyToManyField('Tag')
	related = models.ManyToManyField('self', blank=True)

	def __str__(self):
		return str(self.title)

	class Meta:
		ordering = ["-date"]

	def get_absolute_url(self):
		"""
		Returns the url to access a detail record for this gymnast.
		"""
		return reverse('post-detail', args=[str(self.id)])

class Tag(models.Model):
	name = models.CharField(max_length=100)
	slug = models.SlugField(max_length=130, null=True, blank=True)

	def __str__(self):
		return str(self.name)

	def save(self, *args, **kwargs):
		if not self.id:
			# Newly created object, so set slug
			self.slug = slugify(self.name)

		super(Tag, self).save(*args, **kwargs)

	def get_absolute_url(self):
		return reverse("tag-detail", kwargs={"slug": self.slug})

