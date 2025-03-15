from django.urls import path
from .views import (
    JournalEntryListView,
    JournalEntryDetailView,
    JournalEntryCreateView,
    JournalEntryUpdateView,
    JournalEntryDeleteView,
    preview_polished_entry,
    MyPolishedJournalView,
    download_markdown,
    load_from_markdown,
    markdown_files_list,
    download_markdown_file,
    restore_from_json,
    view_comprehensive_polish_data,
    download_json,
    analytics_view,
    export_to_pdf,
    create_tags,
)
from . import views

urlpatterns = [
    path('', views.home, name='journal-home'),
    path('journal/', views.JournalEntryListView.as_view(), name='journal-home'),
    path('journal/<int:pk>/', views.JournalEntryDetailView.as_view(), name='journal-detail'),
    path('journal/new/', views.JournalEntryCreateView.as_view(), name='journal-create'),
    path('journal/<int:pk>/update/', views.JournalEntryUpdateView.as_view(), name='journal-update'),
    path('journal/<int:pk>/delete/', views.JournalEntryDeleteView.as_view(), name='journal-delete'),
    # path('journal/<int:pk>/polish/', views.polish_journal_entry, name='journal-polish'),
    path('journal/<int:pk>/preview-polish/', views.preview_polished_entry, name='preview-polished-entry'),
    path('my-polished-journal/', views.MyPolishedJournalView.as_view(), name='my-polished-journal'),
    path('journal/<int:pk>/download-markdown/', views.download_markdown, name='download-markdown'),
    path('journal/<int:pk>/load-markdown/', views.load_from_markdown, name='load-markdown'),
    path('journal-entries/', views.JournalEntryListView.as_view(), name='journal-entries'),
    path('markdown-files/', views.markdown_files_list, name='markdown-files'),
    path('download-markdown-file/', views.download_markdown_file, name='download-markdown-file'),
    path('journal/<int:pk>/restore-json/', views.restore_from_json, name='restore-from-json'),
    path('journal/<int:pk>/comprehensive-data/', views.view_comprehensive_polish_data, name='comprehensive-data'),
    path('journal/<int:pk>/download-json/', views.download_json, name='download-json'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('export-pdf/', views.export_to_pdf, name='export-pdf'),
    path('export-pdf/<int:pk>/', views.export_to_pdf, name='export-pdf-entry'),
    path('create-tags/', views.create_tags, name='create-tags'),
] 