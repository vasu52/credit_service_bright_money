from django.urls import path
from . import views

urlpatterns = [
    path('register-user', views.register_user, name='register_user'),
    path('apply-loan', views.apply_loan, name='apply_loan'),
    path('make-payment', views.make_payment, name='make_payment'),
    path('get-statement', views.get_statement, name='get_statement'),
    path('get-users', views.get_users, name='get_users'),
    path('delete-user', views.delete_user, name='delete_user'),
    path('update-user', views.update_user, name='update_user'),
    path('get-loans', views.get_loans, name='get_loans'),
    path('delete-loan', views.delete_loan, name='delete_loan'),
    path('get-bills', views.get_bills, name='get_bills'),
]
