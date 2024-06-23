from rest_framework import serializers
from .models import EMI, User, Loan, Payment, Billing

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class BillingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Billing
        fields = '__all__'

class EMISerializer(serializers.ModelSerializer):
    class Meta:
        model = EMI
        fields = '__all__'
