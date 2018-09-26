from django.shortcuts import render
from django.views import generic
from django.http import HttpResponseRedirect, HttpResponse
import datetime
from dateutil.relativedelta import relativedelta
from django.db.models import Avg, Max
from django.core import paginator
from django.views.generic.detail import SingleObjectMixin
from django.views.generic import ListView
import numpy as np
from .models import Gymnast, Country, Meet, Event, Score, Post, Author, Tag
from django.template import Template, Context

# *******************************
# Pages related to the scores database
# *******************************

# Index
def index(request):
	"""View function for home page of site."""

	# Generate counts of some of the main objects
	num_scores = Score.objects.all().count()
	num_gymnasts = Gymnast.objects.all().count()
	num_meets = Meet.objects.all().count()
	
	# If the form has been sumitted
	result = ""
	to_search = request.GET.get('to_search', False)
	# Search for a gymnast with this name
	if to_search != False:
		try:
			result = Gymnast.objects.get(name__icontains=to_search)
			return HttpResponseRedirect(result.get_absolute_url())
		except Gymnast.DoesNotExist:
			# If no gymnast, search for a meet with this name
			try:
				result = Meet.objects.get(name__icontains=to_search)
				return HttpResponseRedirect(result.get_absolute_url())
			except:
				# Otherwise, return a "not found" message
				result = "Not found. Search again?"

	context={
		'num_scores': num_scores,
		'num_gymnasts': num_gymnasts,
		'num_meets': num_meets,
		'result': result,
	}

	# Render the HTML template index.html with the data in the context variable
	return render(request, 'index.html', context=context)

# About us
def about_us(request):
	"""View function for the About Us page."""
	return render(request, 'about_us.html')

# List of all meets
class MeetListView(generic.ListView):

	model = Meet
	paginate_by = 50

# Detail view for a single gymnast
class GymnastDetailView(generic.DetailView):

	model = Gymnast

	def get_context_data(self, **kwargs):

		context = super(GymnastDetailView, self).get_context_data(**kwargs)

		def get_scores(meet, meet_day, gymnast, event, score_num):
			''' Tries to query a score and returns missing if score does not exist'''
			try:
				score = Score.objects.get(meet=Meet.objects.get(name=meet), meet_day=meet_day, 
					gymnast=Gymnast.objects.get(id=gymnast), 
					event__in=Event.objects.filter(name=event), score_num=score_num)
					# Save just the score value for this score instance
				score = score.score
			except Score.DoesNotExist:
				score = "-"
			return score

		# Get a unique list of meets that have scores for this gymnast
		meets = Score.objects.filter(gymnast=self.object).values_list('meet').distinct()
		to_display = []
		for meet in meets:
			# Get a unique list of meet days when this gymnast competed for each meet 
			meet_days = Score.objects.filter(gymnast=self.object).filter(meet=meet).values_list('meet_day').distinct()
			for day in meet_days:
				# Store the meet instance and meet day
				this_meet_info = [Meet.objects.get(pk=meet[0]), day[0]]
				# Add the VT1, VT2, UB, BB, FX, AA scores to the list
				this_meet_info.append(get_scores(Meet.objects.get(pk=meet[0]).name, day[0], self.object.id, "VT", 1))
				this_meet_info.append(get_scores(Meet.objects.get(pk=meet[0]).name, day[0], self.object.id, "VT", 2))
				this_meet_info.append(get_scores(Meet.objects.get(pk=meet[0]).name, day[0], self.object.id, "UB", 1))
				this_meet_info.append(get_scores(Meet.objects.get(pk=meet[0]).name, day[0], self.object.id, "BB", 1))
				this_meet_info.append(get_scores(Meet.objects.get(pk=meet[0]).name, day[0], self.object.id, "FX", 1))
				# Calculate AA score if applicable
				if day[0] != "EF" and isinstance(this_meet_info[2], float) and isinstance(this_meet_info[4], float) and isinstance(this_meet_info[5], float) and isinstance(this_meet_info[6], float):
					aa_total = float(this_meet_info[2]) + float(this_meet_info[4]) + float(this_meet_info[5]) + float(this_meet_info[6])
					this_meet_info.append(aa_total)
				else:
					this_meet_info.append("-")
				# Add info for this meet day to the list of data to display in the table
				to_display.append(this_meet_info)

		# Add an extra field to the context with the information for the table
		context['to_display'] = to_display
		return context

# Detail view for a single meet
class MeetDetailView(generic.DetailView):

	model = Meet

	def get_context_data(self, **kwargs):

		context = super(MeetDetailView, self).get_context_data(**kwargs)

		# Get a list of unique meet day types for the scores linked to this meet
		days = Score.objects.filter(meet=self.object).values_list('meet_day').distinct()

		# Create a list (gymnast_querysets) where each item is a queryset for all the gymnasts competing on a given day
		# The first item will the the gymnasts with scores for the first day of  context['days'], etc.
		to_display = []
		gymnast_names=[]

		def get_scores(meet, meet_day, gymnast, event, junior, score_num):
			''' Tries to query a score and returns missing if score does not exist'''
			try:
				score = Score.objects.get(meet=Meet.objects.get(name=meet), meet_day=meet_day, 
					gymnast=Gymnast.objects.get(id=gymnast), 
					event=Event.objects.get(name=event, junior=junior), score_num=score_num)
				# Save 1) the score for this istance, and 2) whether the gymnast was a junior
				score = score.score
			except Score.DoesNotExist:
				score = "-"
			return score

		# Loop through the meet days - each one will be a separate table
		for day in days:
			# Test if there was a version of this meet day for juniors and seniors
			has_juniors = (Score.objects.filter(meet=Meet.objects.get(name=self.object), meet_day=day[0], event__in=Event.objects.filter(junior=True)).count() > 0)
			has_seniors = (Score.objects.filter(meet=Meet.objects.get(name=self.object), meet_day=day[0], event__in=Event.objects.filter(junior=False)).count() > 0)
			if has_juniors and has_seniors:
				to_loop = [False, True]
			elif has_juniors and ~has_seniors:
				to_loop = [True]
			elif ~has_juniors and has_seniors:
				to_loop = [False]
			for jr_event in to_loop:
				# If this is not event finals
				if day[0] != "EF":
					# Pull display name for this day
					day_display = Score.objects.filter(meet_day=day[0])[0].get_meet_day_display()
					# Update display name based on whether or not this is the table for juniors, and whether there were any juniors competing at all
					if day_display == "" and has_juniors == True and jr_event == False:
						day_display = "Senior Competition"
					elif day_display == "" and has_juniors == True and jr_event == True:
						day_display = "Junior Competition"
					elif jr_event == True:
						day_display = "Junior " + day_display
					# Get all gymnasts with scores at this meet on this day
					gymnast_queryset=Score.objects.filter(meet=self.object, meet_day=day[0], event__in=Event.objects.filter(junior=jr_event)).values_list('gymnast').distinct()
					gymnast_scores=[]
					for gymnast in gymnast_queryset:
						this_gymnast_scores = []
						this_gymnast_scores.append(Gymnast.objects.get(id=gymnast[0]))
						# Add the VT1, VT2, UB, BB, FX, AA scores to the list
						this_gymnast_scores.append(get_scores(self.object, day[0], gymnast[0], "VT", jr_event, 1))
						this_gymnast_scores.append(get_scores(self.object, day[0], gymnast[0], "VT", jr_event, 2))
						this_gymnast_scores.append(get_scores(self.object, day[0], gymnast[0], "UB", jr_event, 1))
						this_gymnast_scores.append(get_scores(self.object, day[0], gymnast[0], "BB", jr_event, 1))
						this_gymnast_scores.append(get_scores(self.object, day[0], gymnast[0], "FX", jr_event, 1))
						# Calculate the AA score where applicable 
						if isinstance(this_gymnast_scores[1], float) and isinstance(this_gymnast_scores[3], float) and isinstance(this_gymnast_scores[4], float) and isinstance(this_gymnast_scores[5], float):
							 aa_total = float(this_gymnast_scores[1]) + float(this_gymnast_scores[3]) + float(this_gymnast_scores[4]) + float(this_gymnast_scores[5])
							 this_gymnast_scores.append(aa_total)
						else:
							this_gymnast_scores.append("-")
						# Add this list of scores to a list of lists
						gymnast_scores.append(this_gymnast_scores)
					to_display.append((day_display, gymnast_scores))
				# Else, for event finals		
				else:
					# Vault final
					day_display = "Vault Event Final"
					# Update display name based on whether or not this is the table for juniors, and whether there were any juniors competing at all
					if jr_event == True:
						day_display = "Junior " + day_display
					elif has_juniors == True and jr_event == False:
						day_display = "Senior " + day_display
					# Get all gymnasts with vault final at this meet on this day
					gymnast_queryset=Score.objects.filter(meet=self.object).filter(meet_day=day[0]).filter(event=Event.objects.get(name="VT", junior=jr_event)).values_list('gymnast').distinct()
					gymnast_scores=[]
					for gymnast in gymnast_queryset:
						this_gymnast_scores = []
						this_gymnast_scores.append(Gymnast.objects.get(id=gymnast[0]))
						# Add the VT1 and VT2 scores to the list
						this_gymnast_scores.append(get_scores(self.object, day[0], gymnast[0], "VT", jr_event, 1))
						this_gymnast_scores.append(get_scores(self.object, day[0], gymnast[0], "VT", jr_event, 2))
						# Add the vault average score
						if isinstance(this_gymnast_scores[1], float) and isinstance(this_gymnast_scores[2], float):
							 vt_avg = (float(this_gymnast_scores[1]) + float(this_gymnast_scores[2]))/2
							 this_gymnast_scores.append(vt_avg)
						# Add this list of scores to a list of lists
						gymnast_scores.append(this_gymnast_scores)
					to_display.append((day_display, gymnast_scores, "VT"))
					# All other events
					events_list = ["UB", "BB", "FX"]
					for event in events_list:
						event_display = Event.objects.filter(name=event)[0].get_name_display()
						day_display = event_display + " Event Final"
						# Update display name based on whether or not this is the table for juniors, and whether there were any juniors competing at all
						if jr_event == True:
							day_display = "Junior " + day_display
						elif has_juniors == True and jr_event == False:
							day_display = "Senior " + day_display
						# Get all gymnasts in this event final at this meet on this day
						gymnast_queryset=Score.objects.filter(meet=self.object).filter(meet_day=day[0]).filter(event=Event.objects.get(name=event, junior=jr_event)).values_list('gymnast').distinct()
						gymnast_scores=[]
						for gymnast in gymnast_queryset:
							this_gymnast_scores = []
							this_gymnast_scores.append(Gymnast.objects.get(id=gymnast[0]))
							# Add the scores to the list
							this_gymnast_scores.append(get_scores(self.object, day[0], gymnast[0], event, jr_event, 1))
							# Add this list of scores to a list of lists
							gymnast_scores.append(this_gymnast_scores)
						to_display.append((day_display, gymnast_scores, event))

					# Get all gymnasts with scores at this meet 

		# Add an extra field to the context with the list of gymnast querysets
		context['to_display'] = to_display
		return context


# Score Selector 
def score_selector(request):
	"""View function for score selector page of site."""

	# Look for the list of gymnasts entered by the user
	gymnast_list = request.GET.get('gymnast_list', False)

	if gymnast_list:

		# Get the rest of the information submitted through the form
		gymnasts = gymnast_list.split("\r\n")
		event = request.GET.get('event', False)
		sumstat = request.GET.get('sumstat', False)
		time = request.GET.get('time', False)

		# Set the date range 
		now = datetime.datetime.now()
		if time=="year":
			date_range = [now-relativedelta(years=1), now]
		elif time == "season":
			date_range = [datetime.date(2017, 10, 8), now] # Since last world championships
		else:
			date_range = [datetime.date(2016, 8, 21), now] # Since last olympics

		# Get the score data for the results table
		table_data = []
		for gymnast in gymnasts:
			gymnast = Gymnast.objects.get(name=gymnast)
			this_gymnast_scores = []
			this_gymnast_scores.append(gymnast)
			if event == "AA":
				for sub_event in ["VT", "UB", "BB", "FX"]:
					scores = Score.objects.filter(gymnast=gymnast, 
						meet__in=Meet.objects.filter(start_date__range=date_range), event__in=Event.objects.filter(name=sub_event), score_num=1)
					if scores.count() > 0:
						if sumstat == "avg":
							scores_sumstat = scores.aggregate(Avg('score'))['score__avg']
						elif sumstat == "max":
							scores_sumstat = scores.aggregate(Max('score'))['score__max']
					else:
						scores_sumstat = ""
					this_gymnast_scores.append(scores_sumstat)
				# Add up AA average
				if isinstance(this_gymnast_scores[1], float) and isinstance(this_gymnast_scores[2], float) and isinstance(this_gymnast_scores[3], float) and isinstance(this_gymnast_scores[4], float):
					aa_total = float(this_gymnast_scores[1]) + float(this_gymnast_scores[2]) + float(this_gymnast_scores[3]) + float(this_gymnast_scores[4])
					this_gymnast_scores.append(aa_total)
				else:
					this_gymnast_scores.append("")
			elif event == "VT":
				for vt_num in [1, 2]:
					scores = Score.objects.filter(gymnast=gymnast, 
						meet__in=Meet.objects.filter(start_date__range=date_range), event__in=Event.objects.filter(name="VT"), score_num=vt_num)
					if scores.count() > 0:
						if sumstat == "avg":
							scores_sumstat = scores.aggregate(Avg('score'))['score__avg']
						elif sumstat == "max":
							scores_sumstat = scores.aggregate(Max('score'))['score__max']
					else:
						scores_sumstat = ""
					this_gymnast_scores.append(scores_sumstat)
				# Get two-vault average
				if isinstance(this_gymnast_scores[1], float) and isinstance(this_gymnast_scores[2], float):
					vt_avg = (float(this_gymnast_scores[1]) + float(this_gymnast_scores[2]))/2
					this_gymnast_scores.append(vt_avg)
				else:
					this_gymnast_scores.append("")
			else:
				scores = Score.objects.filter(gymnast=gymnast, 
					meet__in=Meet.objects.filter(start_date__range=date_range), event__in=Event.objects.filter(name=event))
				if scores.count() > 0:
					if sumstat == "avg":
						scores_sumstat = scores.aggregate(Avg('score'))['score__avg']
					elif sumstat == "max":
						scores_sumstat = scores.aggregate(Max('score'))['score__max']
				else:
					scores_sumstat = ""
				this_gymnast_scores.append(scores_sumstat)
			table_data.append(this_gymnast_scores)
	else: 
		gymnast_list = ""
		gymnasts = []
		table_data = []
		event = "AA"
		sumstat = "avg"
		time = "year"

	context = {
		'gymnast_list': gymnast_list, # Return what they entered so that it shows up again with the results of their request
		'gymnasts': gymnasts,
		'table_data': table_data,
		'event': event,
		'sumstat': sumstat,
		'time': time,
	}
	return render(request, 'score_selector.html', context=context)



# Score Selector 
def team_tester(request):
	"""View function for score selector page of site."""

	# Look for the team size entered by the user
	team_size = int(request.GET.get('team_size', False))

	# If user has entered information...
	if team_size:

		# Get the rest of the information from the form
		scores_up = int(request.GET.get('scores_up', False))
		scores_count = int(request.GET.get('scores_count', False))
		sumstat = request.GET.get('sumstat', False)
		time = request.GET.get('time', False)
		gymnast_list = []
		for i in range(1, team_size+1):
			gymnast_search_id = "gymnast_search" + str(i)
			gymnast_list.append(request.GET.get(gymnast_search_id, False))

		# Set the date range 
		now = datetime.datetime.now()
		if time=="year":
			date_range = [now-relativedelta(years=1), now]
		elif time == "season":
			date_range = [datetime.date(2017, 10, 8), now] # Since last world championships
		else:
			date_range = [datetime.date(2016, 8, 21), now] # Since last olympics

		# Loop through the list of gymnasts and get scores
		table_data = []
		for gymnast in gymnast_list:
			gymnast = Gymnast.objects.get(name=gymnast)
			this_gymnast_scores = []
			this_gymnast_scores.append(gymnast)
			for sub_event in ["VT", "UB", "BB", "FX"]:
				scores = Score.objects.filter(gymnast=gymnast, 
					meet__in=Meet.objects.filter(start_date__range=date_range), event__in=Event.objects.filter(name=sub_event))
				if scores.count() > 0:
					if sumstat == "avg":
						scores_sumstat = scores.aggregate(Avg('score'))['score__avg']
					elif sumstat == "max":
						scores_sumstat = scores.aggregate(Max('score'))['score__max']
				else:
					scores_sumstat = ""
				this_gymnast_scores.append(scores_sumstat)
			table_data.append(this_gymnast_scores)

		# Select the scores that go up and the scores that count
		for i in range(1, 5):
			# Get the list of all scores on this event
			event_scores = [col[i] for col in table_data]
			# Get the sort order of these scores
			sort_order = np.argsort(np.argsort(event_scores)) # See https://github.com/numpy/numpy/issues/8757
			sort_order = team_size - 1 - sort_order
			# Replace each score with a tuple of the score and the class that we'll use for the td of each score
			for j, row in enumerate(table_data):
				# For scores that count
				if sort_order[j] < scores_count:
					table_data[j][i] = [table_data[j][i], "counts"]
				elif sort_order[j] < scores_up:
					table_data[j][i] = [table_data[j][i], "up"]
				else:
					table_data[j][i] = [table_data[j][i], "not_used"]

		# Calculate total row
		total_row = ["Team Total", 0, 0, 0, 0]
		for row in table_data:
			for i in range(1, 5):
				if row[i][1] == "counts":
					total_row[i] = total_row[i] + row[i][0]
		table_data.append(total_row)
		team_total = sum(total_row[1:5])
		print(table_data)
	else:
		team_size=5
		scores_up=4
		scores_count=3
		sumstat = "avg"
		time = "year"
		gymnast_list = []
		table_data = []
		team_total = ""



	context = {
		'team_size': team_size,
		'scores_up': scores_up,
		'scores_count': scores_count,
		'sumstat': sumstat,
		'time': time,
		'gymnast_list': gymnast_list,
		'table_data': table_data,
		'team_total': team_total,
	}

	return render(request, 'team_tester.html', context=context)

# *******************************
# Pages related to the blog
# *******************************

class PostListView(generic.ListView):

	model = Post
	paginate_by = 5

	def get_context_data(self, **kwargs):

		context = super(PostListView, self).get_context_data(**kwargs)

		# Get list of tags and # of posts in each tag
		tags = []
		for tag in Tag.objects.all():
			to_display = [tag, Post.objects.filter(tag=tag).count()]
			tags.append(to_display)

		tags = sorted(tags, key=lambda tup: tup[1], reverse=True)
		context['tags'] = tags

		return context



class PostDetailView(generic.DetailView):

	model = Post

	def get_context_data(self, **kwargs):

		context = super(PostDetailView, self).get_context_data(**kwargs)
		
		# Pre-render the blog text so that we can parse template code contained within the blog text
		text_to_render = '{% load static %}' + context["post"].text 
		template = Template(text_to_render)
		ctx = Context({'post': context["post"]})
		post_text = template.render(ctx)  # result is 'Your name is Cam'
		context['post_text'] = post_text

		# Get list of tags and # of posts in each tag
		tags = []
		for tag in Tag.objects.all():
			to_display = [tag, Post.objects.filter(tag=tag).count()]
			tags.append(to_display)

		tags = sorted(tags, key=lambda tup: tup[1], reverse=True)
		context['tags'] = tags

		return context

class AuthorDetailView(SingleObjectMixin, ListView):

	model = Author
	paginate_by = 5
	template_name = "scoredata/author_detail.html"
	def get(self, request, *args, **kwargs):
		self.object = self.get_object(queryset=Author.objects.all())
		return super().get(request, *args, **kwargs)

	def get_context_data(self, **kwargs):

		context = super().get_context_data(**kwargs)
		context['author'] = self.object

		# Get list of tags and # of posts in each tag
		tags = []
		for tag in Tag.objects.all():
			to_display = [tag, Post.objects.filter(tag=tag).count()]
			tags.append(to_display)

		tags = sorted(tags, key=lambda tup: tup[1], reverse=True)
		context['tags'] = tags

		return context

	def get_queryset(self):
		return self.object.post_set.all()

class TagDetailView(SingleObjectMixin, ListView):

	model = Tag
	paginate_by = 5
	template_name = "scoredata/tag_detail.html"
	def get(self, request, *args, **kwargs):
		self.object = self.get_object(queryset=Tag.objects.all())
		return super().get(request, *args, **kwargs)

	def get_context_data(self, **kwargs):

		context = super().get_context_data(**kwargs)
		context['author'] = self.object

		# Get list of tags and # of posts in each tag
		tags = []
		for tag in Tag.objects.all():
			to_display = [tag, Post.objects.filter(tag=tag).count()]
			tags.append(to_display)

		tags = sorted(tags, key=lambda tup: tup[1], reverse=True)
		context['tags'] = tags


		return context

	def get_queryset(self):
		return self.object.post_set.all()

# *******************************
# Views that are never seen as actual pages
# *******************************
from django.http import JsonResponse
import json

# For the autocomplete on the homepage, searching BOTH gymnast and meet names
def get_search_names(request):

	if request.is_ajax():
		q = request.GET.get('term', '')
		# Find all gymnast names that start with the inputted letters, and add them to a json
		gymnasts = Gymnast.objects.filter(name__istartswith = q )
		results = []
		for gymnast in gymnasts:
			name_json = {'value': gymnast.name}
			results.append(name_json)
		# FInd all meet names that start with the inputted letters, and add them to the same json
		meets = Meet.objects.filter(name__istartswith = q)
		for meet in meets:
			name_json = {'value': meet.name}
			results.append(name_json)
		data = json.dumps(results)
	else:
		data = 'fail'
	mimetype = 'application/json'
	return HttpResponse(data, mimetype)

# For the autocomplete on the score selector page, which searches just gymnast names
def get_gymnast_names(request):

	if request.is_ajax():
		q = request.GET.get('term', '')
		# Find all gymnast names that start with the inputted letters, and add them to a json
		gymnasts = Gymnast.objects.filter(name__istartswith = q )
		results = []
		for gymnast in gymnasts:
			name_json = {'value': gymnast.name}
			results.append(name_json)
		data = json.dumps(results)
	else:
		data = 'fail'
	mimetype = 'application/json'
	return HttpResponse(data, mimetype)

# For the list of gymnasts on the score selector page, check if the gymnast that the user tried to add exists
def gymnast_validator(request):
	to_search = request.GET.get('to_search', None)
	try:
		gymnast_exists = Gymnast.objects.get(name__iexact=to_search).name
	except Gymnast.DoesNotExist:
		gymnast_exists = False
	data = {
		'gymnast_exists': gymnast_exists
	}
	return JsonResponse(data)
