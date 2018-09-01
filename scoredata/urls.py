from django.urls import path
from django.conf.urls import url
from . import views
from django.views.generic import RedirectView

urlpatterns = [
    path('', views.index, name='index'),
    path('about_us', views.about_us, name='about_us'),
    path('meets/', views.MeetListView.as_view(), name='meets'),
    path('meet/<int:pk>', views.MeetDetailView.as_view(), name='meet-detail'),
    path('gymnast/<uuid:pk>', views.GymnastDetailView.as_view(), name='gymnast-detail'),
    path('score_selector', views.score_selector, name='score_selector'),
    path('team_tester', views.team_tester, name='team_tester'),
    path('posts/', views.PostListView.as_view(), name='posts'),
    path('post/<int:pk>', views.PostDetailView.as_view(), name='post-detail'),
    path('author/<slug>', views.AuthorDetailView.as_view(), name='author-detail'),
    path('tag/<slug>/', views.TagDetailView.as_view(), name='tag-detail'),
    path('get_search_names/', views.get_search_names, name="get_search_names"),
    path('get_gymnast_names/', views.get_search_names, name="get_search_names"),
    path('gymnast_validator/', views.gymnast_validator, name="gymnast_validator"),

]
