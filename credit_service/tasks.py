from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from .models import EMI, User, Loan, Billing
import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def calculate_credit_score(self, user_id):
    logger.debug(f"Task calculate_credit_score called with user_id: {user_id}")
    try:
        user = User.objects.get(id=user_id)
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_file_path = os.path.join(BASE_DIR, 'credit_service', 'data', 'transactions.csv')
        df = pd.read_csv(csv_file_path, encoding='utf-8')

        if 'user' not in df.columns or 'transaction_type' not in df.columns or 'amount' not in df.columns:
            logger.error("Required columns are missing in the CSV file")
            return

        df['user'] = df['user'].astype(str)
        user_id_str = str(user_id)
        user_transactions = df[df['user'] == user_id_str]
        credit_amount = user_transactions[user_transactions['transaction_type'] == 'CREDIT']['amount'].sum()
        debit_amount = user_transactions[user_transactions['transaction_type'] == 'DEBIT']['amount'].sum()
        account_balance = credit_amount - debit_amount

        if account_balance >= 1000000:
            user.credit_score = 900
        elif account_balance <= 10000:
            user.credit_score = 300
        else:
            user.credit_score = 300 + int((account_balance - 10000) // 15000) * 10

        user.save()
        logger.info(f"Credit score for user {user_id} calculated successfully")

    except User.DoesNotExist:
        logger.error(f"User with id {user_id} does not exist")
    except FileNotFoundError:
        logger.error(f"File not found at {csv_file_path}")
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)

@shared_task()
def bill_users():
    today = timezone.now().date()
    loans = Loan.objects.filter(is_closed=False)
    for loan in loans:
        billing_date = loan.disbursement_date + timedelta(days=30)
        paid_EMIs = EMI.objects.filter(loan=loan, is_paid=True).count()
        term_period_curr = loan.term_period - paid_EMIs
        while billing_date <= today:
            interest_accrued = loan.interest_due / term_period_curr
            principal_due_pm = loan.principal_due / term_period_curr
            min_due = interest_accrued + principal_due_pm
            due_date = billing_date + timedelta(days=15)
            Billing.objects.create(
                loan=loan,
                billing_date=billing_date,
                due_date=due_date,
                principal_balance=loan.principal_due,
                apr=loan.interest_rate,
                min_due=min_due,
            )
            billing_date += timedelta(days=30)