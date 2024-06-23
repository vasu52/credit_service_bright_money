from datetime import timedelta
from decimal import Decimal
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.db import transaction
from .models import Billing, User, Loan, Payment, EMI
from .serializers import BillingSerializer, UserSerializer, LoanSerializer
from credit_service.tasks import calculate_credit_score

@api_view(['POST'])
def register_user(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        calculate_credit_score.delay(user.id)
        serialized_user = UserSerializer(user)
        return Response(serialized_user.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def apply_loan(request):
    user = User.objects.get(id=request.data['user'])
    if user.credit_score < 450:
        return Response({"error": "User's credit score is less than 450"}, status=status.HTTP_400_BAD_REQUEST)
    if user.annual_income < 150000:
        return Response({"error": "User's annual income is less than 1,50,000"}, status=status.HTTP_400_BAD_REQUEST)
    if int(request.data['loan_amount']) > 5000 or int(request.data['loan_amount'])<=0:
        return Response({"error": "Incorrect Loan Amount"}, status=status.HTTP_400_BAD_REQUEST)
    if(int(request.data['interest_rate'])<12):
        return Response({"error": "Interest rate must be greater than 12"}, status=status.HTTP_400_BAD_REQUEST)
    calc_apr = int(request.data['loan_amount']) * (int(request.data['interest_rate']) * (Decimal(request.data['term_period']) / 12)) / 100 / int(request.data['term_period'])
    print(calc_apr)
    if calc_apr < 50:
        return Response({"error": "Interest rate is too low, apr < 50 for a month"}, status=status.HTTP_400_BAD_REQUEST)
    total_monthly_due = Decimal(int(request.data['loan_amount']) / Decimal(request.data['term_period'])) + calc_apr
    if total_monthly_due * 5 > user.annual_income / 12:
        return Response({"error": "EMI exceeds 20 percent of user's monthly income"}, status=status.HTTP_400_BAD_REQUEST)
    request.data['principal_due']=round(Decimal(request.data['loan_amount']),2)
    request.data['interest_due']=int(request.data['loan_amount']) * (int(request.data['interest_rate']) * (Decimal(request.data['term_period']) / 12)) / 100
    serializer = LoanSerializer(data=request.data)
    if serializer.is_valid():
        loan = serializer.save()
        emi_amount = total_monthly_due
        for i in range(loan.term_period):
            emi_due_date = loan.disbursement_date + timedelta(days=30 * (i+1))
            EMI.objects.create(loan=loan, due_date=emi_due_date, amount_due=emi_amount)
        
        upcoming_emis = EMI.objects.filter(loan=loan, is_paid=False).order_by('due_date')
        upcoming_transactions = [
            {
                'date': emi.due_date,
                'amount_due': emi.amount_due
            }
            for emi in upcoming_emis
        ]
        loan_data = LoanSerializer(loan)
        response_data = {
            'loan-details': loan_data.data,
            'upcoming_transactions': upcoming_transactions
        }
        return Response(response_data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def make_payment(request):
    loan_id = request.data['loan_id']
    amount = Decimal(request.data['amount'])
    date = request.data['date']
    
    try:
        loan = Loan.objects.get(id=loan_id)
    except Loan.DoesNotExist:
        return Response({'error': 'Loan not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    if loan.is_closed:
        return Response({'error': 'Loan is already closed'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        with transaction.atomic():
            last_payment = Payment.objects.filter(loan=loan).order_by('date').last()
            if last_payment and last_payment.date == request.data['date']:
                return Response({'error': 'Payment for this date already recorded'}, status=status.HTTP_400_BAD_REQUEST)

            next_emi = EMI.objects.filter(loan=loan, is_paid=False).order_by('due_date').first()
            if not next_emi:
                return Response({'error': 'No upcoming EMIs found'}, status=status.HTTP_400_BAD_REQUEST)

            paid_EMIs = EMI.objects.filter(loan=loan, is_paid=True).count()
            term_period_curr = loan.term_period - paid_EMIs
            monthly_interest = loan.interest_due / term_period_curr
            temp_amt = amount
            loan.interest_due -= min(monthly_interest, temp_amt)
            temp_amt -= min(monthly_interest,temp_amt)
            loan.principal_due-=temp_amt

            if amount == next_emi.amount_due:
                next_emi.amount_due -= amount
                next_emi.is_paid = True
                next_emi.save()
                if loan.principal_due <= 0:
                    loan.is_closed = True
                    loan.save()    
                payment = Payment(loan=loan, amount=amount, date = date, \
                                principal_due=loan.principal_due, interest_due=loan.interest_due)
                payment.save()    
                return Response({'message': 'Payment recorded successfully'}, status=status.HTTP_200_OK) 
            loan.save()
            temp_amt = amount
            while temp_amt>0:
                next_emi = EMI.objects.filter(loan=loan, is_paid=False).order_by('due_date').first()
                if not next_emi:
                    break
                subtracted = min(next_emi.amount_due,temp_amt)
                next_emi.amount_due-=subtracted
                temp_amt-=subtracted
                if next_emi.amount_due==0:
                    next_emi.is_paid=True
                next_emi.save()
            EMI.objects.filter(loan=loan, is_paid=False).delete()
            recalculate_emis(loan)
            payment = Payment(loan=loan, amount=amount, date=date,\
                            principal_due=loan.principal_due, interest_due=loan.interest_due)
            payment.save()

            return Response({'message': 'Payment recorded successfully, '}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def recalculate_emis(loan):
    remaining_principal = loan.principal_due
    remaining_interest = loan.interest_due

    paid_EMIs = EMI.objects.filter(loan=loan, is_paid=True).count()

    for i in range(paid_EMIs, loan.term_period):
        emi_due_date = loan.disbursement_date + timedelta(days=30 * (i + 1))
        interest_for_month = remaining_interest / (loan.term_period - paid_EMIs)
        principal_for_month = remaining_principal / (loan.term_period - paid_EMIs)
        emi_amount_due = interest_for_month + principal_for_month

        emi = EMI(
            loan=loan,
            due_date=emi_due_date,
            amount_due=emi_amount_due,
            is_paid=False
        )
        emi.save()


@api_view(['GET'])
def get_statement(request):
    loan_id = request.query_params.get('loan_id')
    try:
        loan = Loan.objects.get(id=loan_id)
    except Loan.DoesNotExist:
        return Response({'error': 'Loan not found'}, status=status.HTTP_400_BAD_REQUEST)

    if loan.is_closed:
        return Response({'error': 'Loan is closed'}, status=status.HTTP_400_BAD_REQUEST)

    payments = Payment.objects.filter(loan=loan).order_by('date')
    total_paid = 0
    for payment in payments:
        total_paid+=payment.amount

    past_transactions = [
        {
            'date': payment.date,
            'amount_paid': payment.amount,
            'principal_due': payment.principal_due,
            'interest_due': payment.interest_due,
        }
        for payment in payments
    ]


    upcoming_emis = EMI.objects.filter(loan=loan, is_paid=False).order_by('due_date')
    upcoming_transactions = [
        {
            'date': emi.due_date,
            'amount_due': emi.amount_due
        }
        for emi in upcoming_emis
    ]

    response_data = {
        'principal-due': loan.principal_due,
        'interest-due': loan.interest_due,
        'amount-paid': total_paid,
        'past_transactions': past_transactions,
        'upcoming_transactions': upcoming_transactions
    }
    return Response(response_data, status=status.HTTP_200_OK)


# views for data manipulation for testing

@api_view(['GET'])
def get_users(request):
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_loans(request):
    loans = Loan.objects.all()
    serializer = LoanSerializer(loans, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_bills(request):
    bills = Billing.objects.all()
    serializer = BillingSerializer(bills, many=True)
    return Response(serializer.data)

@api_view(['DELETE'])
def delete_user(request):
    user_id = request.query_params.get('user_id')
    try:
        user = User.objects.get(id=user_id)
        user.delete()
        return Response("User deleted successfully", status=status.HTTP_204_NO_CONTENT)
    except User.DoesNotExist:
        return Response("User not found", status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
def delete_loan(request):
    loan_id = request.query_params.get('loan_id')
    try:
        loan = Loan.objects.get(id=loan_id)
        loan.delete()
        return Response("Loan deleted successfully", status=status.HTTP_204_NO_CONTENT)
    except Loan.DoesNotExist:
        return Response("Lona not found", status=status.HTTP_404_NOT_FOUND)

@api_view(['PUT'])
def update_user(request):
    user_id = request.query_params.get('user_id')
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
