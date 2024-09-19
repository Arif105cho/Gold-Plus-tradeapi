from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class GoldHolding(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    gold_in_grams = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Gold owned by the user
    balance_in_currency = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Currency balance of the user

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPES)
    gold_in_grams = models.DecimalField(max_digits=10, decimal_places=2)
    amount_in_currency = models.DecimalField(max_digits=12, decimal_places=2)
    commission_applied = models.DecimalField(max_digits=5, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
