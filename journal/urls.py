from django.urls import path
from .views import (
    JournalEntryListView,
    JournalEntryDetailView,
    JournalEntryCreateView,
    JournalEntryUpdateView,
    JournalEntryDeleteView,
    polish_journal_entry,
    preview_polished_entry,
    MyPolishedJournalView
)
from . import views

urlpatterns = [
    path('', views.home, name='journal-home'),
    path('journal/', JournalEntryListView.as_view(), name='journal-entries'),
    path('journal/<int:pk>/', JournalEntryDetailView.as_view(), name='journal-detail'),
    path('journal/new/', JournalEntryCreateView.as_view(), name='journal-create'),
    path('journal/<int:pk>/update/', JournalEntryUpdateView.as_view(), name='journal-update'),
    path('journal/<int:pk>/delete/', JournalEntryDeleteView.as_view(), name='journal-delete'),
    path('journal/<int:pk>/polish/', polish_journal_entry, name='journal-polish'),
    path('journal/<int:pk>/preview/', preview_polished_entry, name='preview-polished-entry'),
    path('my-polished-journal/', MyPolishedJournalView.as_view(), name='my-polished-journal'),
] 