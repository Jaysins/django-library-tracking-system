from datetime import timedelta

from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from .models import Author, Book, Member, Loan
from .serializers import AuthorSerializer, BookSerializer, MemberSerializer, LoanSerializer
from rest_framework.decorators import action, api_view
from django.utils import timezone
from .tasks import send_loan_notification


class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        """

        """
        return Book.objects.select_related('author').all()

    @action(detail=True, methods=['post'])
    def loan(self, request, pk=None):
        book = self.get_object()
        if book.available_copies < 1:
            return Response({'error': 'No available copies.'}, status=status.HTTP_400_BAD_REQUEST)
        member_id = request.data.get('member_id')
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return Response({'error': 'Member does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan = Loan.objects.create(book=book, member=member)
        book.available_copies -= 1
        book.save()
        send_loan_notification.delay(loan.id)
        return Response({'status': 'Book loaned successfully.'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        book = self.get_object()
        member_id = request.data.get('member_id')
        try:
            loan = Loan.objects.get(book=book, member__id=member_id, is_returned=False)
        except Loan.DoesNotExist:
            return Response({'error': 'Active loan does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan.is_returned = True
        loan.return_date = timezone.now().date()
        loan.save()
        book.available_copies += 1
        book.save()
        return Response({'status': 'Book returned successfully.'}, status=status.HTTP_200_OK)


class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer

    @action(detail=False, methods=['get'], url_path='top-active',
            url_name='top_active')
    def top_active_members(self, request):
        members = Member.objects.annotate(active_loans=Count('loans', filter=Q(
            loans__is_returned=False))).order_by(
            '-active_loan')[:5]

        data = [{
            "id": member.id,
            "username": member.user.username,
            "email": member.user.email,
            "active_loans": member.active_loans
        } for member in members]

        return Response(data)


class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer

    @action(detail=True, methods=['post'])
    def extend_due_date(self, request, pk=None):
        """

        """

        additional_days = request.data.get("additional_days")

        try:
            additional_days = int(additional_days)
            if additional_days <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response({
                'error': "Additional days cannot be zero or less than 0"
            }, status=status.HTTP_400_BAD_REQUEST)

        loan = self.get_object()

        if loan.due_date < timezone.now():
            return Response({
                'error': "Cannot extend due date for an overdue loan"
            }, status=status.HTTP_400_BAD_REQUEST)

        loan.due_date += timedelta(days=additional_days)

        loan.save()

        return Response(self.get_serializer(loan).data,
                        status=status.HTTP_200_OK)