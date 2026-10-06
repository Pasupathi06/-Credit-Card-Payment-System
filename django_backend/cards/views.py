from rest_framework import generics, permissions

from .models import Card
from .serializers import CardSerializer


class CardListCreateView(generics.ListCreateAPIView):
    serializer_class = CardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Card.objects.filter(
            user=self.request.user
        )


class CardDeleteView(generics.DestroyAPIView):
    serializer_class = CardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Card.objects.filter(
            user=self.request.user
        )


class AdminCardListView(generics.ListAPIView):
    serializer_class = CardSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Card.objects.all().select_related("user")