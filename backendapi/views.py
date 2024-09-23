from rest_framework import generics, status
from rest_framework.response import Response
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, LoginSerializer,TransactionSerializer
from .models import GoldHolding, Transaction
from .utils import convert_grams_to_currency, apply_commission, check_user_balance
import requests
import redis
from django.core.cache import cache
from django.conf import settings
from rest_framework.decorators import api_view
from threading import Thread, Lock
from django.db import transaction

lock = Lock()


# Redis configuration
REDIS_TTL = 300  # Time-to-Live in seconds (5 minutes)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": serializer.data,
            "message": "Account created successfully"
        }, status=status.HTTP_201_CREATED)

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_gold_price(request):
    # Check if the price is cached in Redis
    gold_price = cache.get('gold_price')
    print("check cache gold price" , gold_price)
    if gold_price is None:
        # If not in cache, fetch the gold price from the API
        api_key = "goldapi-ek0lsm185q1sd-io"
        url = "https://www.goldapi.io/api/XAU/INR/20240918"
        
        headers = {
            "x-access-token": api_key,
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(url, headers=headers)
            print({'response':response.json()})
            response.raise_for_status()

            gold_price_data = response.json()
            print("gold price get",get_gold_price)
            gold_price = gold_price_data.get('price')

            if gold_price:
                # Store the price in Redis with TTL of 5 minutes
                cache.set('gold_price', gold_price, timeout=REDIS_TTL)
                return Response({'gold_price': gold_price}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Unable to fetch gold price.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except requests.RequestException as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Return the cached gold price
    return Response({'gold_price': gold_price}, status=status.HTTP_200_OK)



# Constants
COMMISSION_RATE = 0.02  # 2% commission
GOLD_PRICE_API_URL = "https://www.goldapi.io/api/XAU/INR/20240917"
GOLD_API_KEY = "goldapi-ek0lsm185q1sd-io"

def fetch_current_gold_price():
    """Fetch the current gold price from an API."""
    headers = {
        "x-access-token": GOLD_API_KEY,
        "Content-Type": "application/json"
    }
    
    response = requests.get(GOLD_PRICE_API_URL, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    return data.get('price')


@api_view(['POST'])
def buy_gold(request):
    user = request.user
    grams_to_buy = request.data.get('grams')
    
    if not grams_to_buy:
        return Response({'error': 'Grams field is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        gold_price_per_gram = fetch_current_gold_price()
    except requests.RequestException as e:
        return Response({'error': 'Failed to fetch gold price.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    amount_to_pay = convert_grams_to_currency(grams_to_buy, gold_price_per_gram)
    total_amount_with_commission = apply_commission(amount_to_pay, COMMISSION_RATE)

    if not check_user_balance(user, total_amount_with_commission):
        return Response({'error': 'Insufficient balance.'}, status=status.HTTP_400_BAD_REQUEST)

    def process_transaction():
        with lock:
            with transaction.atomic():
                user.goldholding.balance_in_currency -= total_amount_with_commission
                user.goldholding.gold_in_grams += float(grams_to_buy)
                user.goldholding.save()

                Transaction.objects.create(
                    user=user,
                    transaction_type='buy',
                    gold_in_grams=grams_to_buy,
                    amount_in_currency=amount_to_pay,
                    commission_applied=total_amount_with_commission - amount_to_pay
                )

    transaction_thread = Thread(target=process_transaction)
    transaction_thread.start()
    transaction_thread.join()

    return Response({
        'message': f'Successfully bought {grams_to_buy} grams of gold.',
        'total_amount': total_amount_with_commission,
        'remaining_balance': user.goldholding.balance_in_currency,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def sell_gold(request):
    user = request.user
    grams_to_sell = request.data.get('grams')

    if not grams_to_sell:
        return Response({'error': 'Grams field is required.'}, status=status.HTTP_400_BAD_REQUEST)

    if user.goldholding.gold_in_grams < float(grams_to_sell):
        return Response({'error': 'Insufficient gold balance.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        gold_price_per_gram = fetch_current_gold_price()
    except requests.RequestException as e:
        return Response({'error': 'Failed to fetch gold price.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    amount_to_receive = convert_grams_to_currency(grams_to_sell, gold_price_per_gram)
    total_amount_with_commission = apply_commission(amount_to_receive, COMMISSION_RATE)

    def process_transaction():
        with lock:
            with transaction.atomic():
                user.goldholding.balance_in_currency += total_amount_with_commission
                user.goldholding.gold_in_grams -= float(grams_to_sell)
                user.goldholding.save()

                Transaction.objects.create(
                    user=user,
                    transaction_type='sell',
                    gold_in_grams=grams_to_sell,
                    amount_in_currency=amount_to_receive,
                    commission_applied=total_amount_with_commission - amount_to_receive
                )

    transaction_thread = Thread(target=process_transaction)
    transaction_thread.start()
    transaction_thread.join()

    return Response({
        'message': f'Successfully sold {grams_to_sell} grams of gold.',
        'total_amount_received': total_amount_with_commission,
        'remaining_balance': user.goldholding.balance_in_currency,
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_transaction_history(request):
    user = request.user
    transactions = Transaction.objects.filter(user=user).order_by('-date')
    serializer = TransactionSerializer(transactions, many=True)
    return serializer.data