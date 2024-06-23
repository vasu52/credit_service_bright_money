from django.db import models
from uuid import uuid4
from datetime import date

class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=True)
    aadhar_id = models.CharField(max_length=12, unique=True)
    name = models.CharField(max_length=100)
    email_id = models.EmailField(unique=True)
    annual_income = models.DecimalField(max_digits=10, decimal_places=2)
    credit_score = models.IntegerField(default=0)
    account_created = models.DateField(auto_now_add=True)

class Loan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    loan_amount = models.DecimalField(max_digits=10, decimal_places=2)
    loan_type = models.CharField(max_length=20, default='Credit Card Loan')
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    term_period = models.IntegerField()
    disbursement_date = models.DateField()
    principal_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    interest_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_closed = models.BooleanField(default=False)

class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    principal_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    interest_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date = models.DateField(auto_now_add=True)

class Billing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    billing_date = models.DateField()
    due_date = models.DateField()
    min_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    principal_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    apr = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateField(auto_now_add=True)

class EMI(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)
