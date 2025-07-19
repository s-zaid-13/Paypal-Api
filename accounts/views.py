from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from .models import User
from .serializers import UserSubscriptionSerializer


class AllUsersWithSubscriptionView(APIView):
    # permission_classes = [IsAdminUser]
    def get(self, request):
        users = User.objects.all().order_by("-is_subscribed")
        serializer = UserSubscriptionSerializer(users, many=True)
        return Response(serializer.data)
