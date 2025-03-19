import random

from faker import Faker
from library.models import Member, User, Book, Author, Loan
from datetime import timedelta
from django.utils import timezone

fake = Faker()

members = []

for _ in range(5):
    user = User.objects.create(
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        username=fake.user_name(),
        email=fake.email()
    )
    member = Member.objects.create(
        user_id=user.id, )
    members.append(member)
books = []

for _ in range(10):
    author = Author.objects.create(
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        biography=fake.sentence(nb_words=10)
    )
    book = Book.objects.create(
        title=fake.sentence(nb_words=4),
        author_id=author.id,
        isbn=fake.text(max_nb_chars=5) + str(author.id),
        genre=random.choice(['fiction', 'nonfiction', 'sci-fi', 'biography']),
        available_copies=2
    )
    books.append(book)

for _ in range(15):
    member = random.choice(members)
    book = random.choice(books)
    loan_date = fake.date_time_between(start_date='-30d', end_date='now', tzinfo=timezone.get_current_timezone())
    due_date = loan_date + timedelta(days=14)
    is_returned = random.choice([True, False])
    if not is_returned and random.random() < 0.3:
        due_date = loan_date + timedelta(days=7)
    Loan.objects.create(
        member_id=member.id,
        book_id=book.id,
        loan_date=loan_date,
        due_date=due_date,
        is_returned=is_returned
    )

