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
# analytics/api.py
from analytics.models import SMTPConfiguration
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

@api_view(["GET"])
def get_smtp_config(request):
    cfg = SMTPConfiguration.objects.get(smtp_client_name="DEFAULT")
    return Response({
        "host": cfg.smtp_email_host,
        "port": cfg.smtp_email_port,
        "use_tls": cfg.smtp_email_use_tls,
        "username": cfg.smtp_email_host_user,
        "password": cfg.smtp_email_host_password,
        "aws_access_key": cfg.access_key_id,
        "aws_secret": cfg.aws_secret_key,
        "region": cfg.aws_region,
        "email_type": cfg.email_type
    })
