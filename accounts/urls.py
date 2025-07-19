from django.urls import include, path
from .views import *
urlpatterns = [

    # accounts creation
    path('signup/', signup, name='signup'),
    path('login/', login, name='login'),
    path('profile/', profile, name='profile'),
    path('logout/', logout, name='logout'),

    # accounts update 
    path('change_email/', change_email, name='change_email'),
    path('change_password/', change_password, name='change_password'),
    path('change_username/', change_username, name='change_username'),
    path('change_first_name/', change_first_name, name='change_first_name'),
    path('change_last_name/', change_last_name, name='change_last_name'),
    
    #test path
    #path('index/', index, name='index')
]
