from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)
from .models import JournalEntry
from .utils import polish_text
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)


def home(request):
    return render(request, 'journal/home.html')


class JournalEntryListView(LoginRequiredMixin, ListView):
    model = JournalEntry
    template_name = 'journal/journal_entries.html'
    context_object_name = 'entries'
    ordering = ['-date_posted']

    def get_queryset(self):
        return JournalEntry.objects.filter(author=self.request.user).order_by('-date_posted')


class JournalEntryDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = JournalEntry

    def test_func(self):
        entry = self.get_object()
        return self.request.user == entry.author

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        polished_content = request.POST.get('polished_content')
        if polished_content:
            self.object.polished_content = polished_content
            self.object.save()
            messages.success(request, 'Polished content saved successfully!')
        return redirect(self.get_success_url())

    def get_success_url(self):
        return self.object.get_absolute_url()


class JournalEntryCreateView(LoginRequiredMixin, CreateView):
    model = JournalEntry
    fields = ['title', 'content']
    success_url = '/journal/'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class JournalEntryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = JournalEntry
    fields = ['title', 'content']
    success_url = '/journal/'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def test_func(self):
        entry = self.get_object()
        return self.request.user == entry.author


class JournalEntryDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = JournalEntry
    success_url = '/journal/'

    def test_func(self):
        entry = self.get_object()
        return self.request.user == entry.author


@login_required
def polish_journal_entry(request, pk):
    """View to handle AI polishing of a journal entry."""
    entry = get_object_or_404(JournalEntry, pk=pk, author=request.user)

    if request.method == 'POST':
        # Call the OpenAI API to polish the text
        polished_content = polish_text(entry.content)

        if polished_content:
            entry.polished_content = polished_content
            entry.is_polished = True  # Set the entry as polished
            entry.save()
            messages.success(request, 'Your journal entry has been polished!')
        else:
            messages.error(
                request, 'Failed to polish your journal entry. Please try again later.')

    return redirect('journal-detail', pk=entry.pk)


@login_required
def preview_polished_entry(request, pk):
    """View to preview the polished journal entry and detect its topic."""
    entry = get_object_or_404(JournalEntry, pk=pk, author=request.user)

    if request.method == 'POST':
        # Call the OpenAI API to polish the text and detect the topic
        polished_content, topic = polish_text(entry.content)

        if polished_content:
            return render(request, 'journal/preview_polished_entry.html', {
                'entry': entry,
                'polished_content': polished_content,
                'topic': topic
            })
        else:
            messages.error(
                request, 'Failed to polish your journal entry. Please try again later.')

    return redirect('journal-detail', pk=entry.pk)


class MyPolishedJournalView(LoginRequiredMixin, ListView):
    model = JournalEntry
    template_name = 'journal/my_polished_journal.html'
    context_object_name = 'polished_entries'

    def get_queryset(self):
        return JournalEntry.objects.filter(author=self.request.user, is_polished=True).order_by('-date_posted')


def polish_entry(request, entry_id):
    entry = get_object_or_404(JournalEntry, id=entry_id)
    if request.method == 'POST':
        # Assume you have a function to polish the content
        # Replace with your polishing logic
        polished_content = polish_content(entry.content)
        entry.polished_content = polished_content
        entry.save()
        # Redirect to the polished journal list
        return redirect('my-polished-journal')
    return render(request, 'journal/journalentry_detail.html', {'object': entry})


def my_polished_journal(request):
    polished_entries = JournalEntry.objects.filter(
        polished_content__isnull=False)
    # Log the polished entries
    logger.debug(f"Polished Entries: {polished_entries}")
    return render(request, 'journal/my_polished_journal.html', {'polished_entries': polished_entries})
