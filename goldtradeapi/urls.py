"""
URL configuration for goldtradeapi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from backendapi import views 

urlpatterns = [
    path('register/',views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('gold-price/', views.get_gold_price, name='gold-price'),
    path('buy-gold/', views.buy_gold, name='buy-gold'),
    path('sell-gold/', views.sell_gold, name='sell-gold'),
    path('transection-history',views.get_transaction_history),
    path('admin',admin.site.urls)

]
