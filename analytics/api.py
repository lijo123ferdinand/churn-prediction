# analytics/api.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from users.models import User

@api_view(['GET'])
def get_churn_score(request, user_id):
    user = User.objects.get(id=user_id)
    return Response({
        "username": user.username,
        "churn_score": user.churn_score
    })
