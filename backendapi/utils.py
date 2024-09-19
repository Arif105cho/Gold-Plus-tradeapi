def convert_grams_to_currency(grams, gold_price_per_gram):
    """Convert grams of gold to equivalent currency based on current price."""
    return grams * gold_price_per_gram

def apply_commission(amount, commission_rate):
    """Apply commission to a given amount."""
    return amount * (1 + commission_rate)

def check_user_balance(user, required_amount):
    """Check if the user has enough balance for a transaction."""
    if user.goldholding.balance_in_currency < required_amount:
        return False
    return True
