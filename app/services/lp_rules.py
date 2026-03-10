from dataclasses import dataclass

# We store digit as int:
# 2-9 = themselves
# 10 = "0"
# 11 = "A"
DIGIT_ORDER = [2,3,4,5,6,7,8,9,10,11]

@dataclass
class ParsedBid:
    count: int
    digit: int
    raw: str

def parse_final_bid(raw: str) -> ParsedBid:
    s = raw.strip().upper().replace(" ", "")
    if len(s) < 2:
        raise ValueError("final_bid_raw must look like '8A' or '110'")

    last = s[-1]
    count_str = s[:-1]
    if not count_str.isdigit():
        raise ValueError("final bid must start with a number (count)")

    count = int(count_str)

    if last == "A":
        digit = 11
    elif last == "0":
        digit = 10
    elif last.isdigit():
        d = int(last)
        if d < 2 or d > 9:
            raise ValueError("digit must be 2-9, 0, or A")
        digit = d
    else:
        raise ValueError("digit must be 2-9, 0, or A")

    return ParsedBid(count=count, digit=digit, raw=s)

def compute_payout(base_bet: float, is_nut: bool, is_skunk: bool) -> float:
    mult = 1
    if is_nut:
        mult *= 2
    if is_skunk:
        mult *= 2
    return float(base_bet) * mult