from missions.models import Complaint


def compute_sentiment(rating, message=''):
    if not message or not str(message).strip():
        return Complaint.Sentiment.UNKNOWN
    if rating >= 4:
        return Complaint.Sentiment.POSITIVE
    if rating == 3:
        return Complaint.Sentiment.NEUTRAL
    return Complaint.Sentiment.NEGATIVE
