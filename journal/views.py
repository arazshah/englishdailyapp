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
from .models import JournalEntry, Tag
from .utils import polish_text, save_polish_data_to_json, get_latest_polish_data, render_to_pdf
from django.urls import reverse
import logging
from django.http import FileResponse, HttpResponse, JsonResponse
import os
from datetime import datetime, timedelta
from django.conf import settings
import json
from django.db.models import Q, Func, F, Avg, Count
from django.utils import timezone

logger = logging.getLogger(__name__)


def home(request):
    return render(request, 'journal/home.html')


class JournalEntryListView(LoginRequiredMixin, ListView):
    model = JournalEntry
    template_name = 'journal/journal_entries.html'
    context_object_name = 'entries'
    paginate_by = 10

    def get_queryset(self):
        queryset = JournalEntry.objects.filter(author=self.request.user)
        
        # Search
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(content__icontains=search_query)
            )
        
        # Tag filter
        tag_id = self.request.GET.get('tag')
        if tag_id:
            queryset = queryset.filter(tags__id=tag_id)
        
        # Polished filter
        polished = self.request.GET.get('polished')
        if polished == '1':
            queryset = queryset.filter(is_polished=True)
        elif polished == '0':
            queryset = queryset.filter(is_polished=False)
        
        # Date range
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(date_posted__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(date_posted__lte=date_to)
        
        return queryset.order_by('-date_posted')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tags'] = Tag.objects.filter(user=self.request.user)
        return context


class JournalEntryDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = JournalEntry

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get total entries count
        context['total_entries'] = JournalEntry.objects.filter(author=self.request.user).count()
        
        # Get polished entries count
        context['polished_entries'] = JournalEntry.objects.filter(
            author=self.request.user, 
            is_polished=True
        ).count()
        
        # Get monthly entries count
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        context['monthly_entries'] = JournalEntry.objects.filter(
            author=self.request.user,
            date_posted__gte=month_start
        ).count()
        
        # Get recent entries
        context['recent_entries'] = JournalEntry.objects.filter(
            author=self.request.user
        ).exclude(
            id=self.object.id
        ).order_by('-date_posted')[:5]
        
        # Get related entries (entries with the same tags)
        if self.object.tags.exists():
            tag_ids = self.object.tags.values_list('id', flat=True)
            context['related_entries'] = JournalEntry.objects.filter(
                author=self.request.user,
                tags__id__in=tag_ids
            ).exclude(
                id=self.object.id
            ).distinct().order_by('-date_posted')[:5]
        
        # Parse metrics data if it exists
        if self.object.metrics_data and isinstance(self.object.metrics_data, str):
            try:
                context['metrics_data'] = json.loads(self.object.metrics_data)
            except json.JSONDecodeError:
                context['metrics_data'] = {}
        else:
            context['metrics_data'] = self.object.metrics_data or {}
        
        return context
    
    def test_func(self):
        entry = self.get_object()
        return self.request.user == entry.author
    
    def post(self, request, *args, **kwargs):
        entry = self.get_object()
        
        # Handle saving polished content
        if 'polished_content' in request.POST and 'is_polished' in request.POST:
            entry.polished_content = request.POST.get('polished_content')
            entry.is_polished = True
            entry.polish_date = timezone.now()
            
            # Save additional polish data if available
            if 'evaluation' in request.POST:
                entry.evaluation = request.POST.get('evaluation')
            
            if 'topic' in request.POST:
                entry.topic = request.POST.get('topic')
            
            if 'diff_html' in request.POST:
                entry.diff_html = request.POST.get('diff_html')
            
            if 'metrics_data' in request.POST:
                try:
                    entry.metrics_data = json.loads(request.POST.get('metrics_data'))
                except json.JSONDecodeError:
                    # If JSON parsing fails, store as string
                    entry.metrics_data = request.POST.get('metrics_data')
            
            entry.save()
            
            # Save as markdown if configured
            if getattr(settings, 'SAVE_AS_MARKDOWN', False):
                entry.save_as_markdown()
            
            messages.success(request, 'Your journal entry has been polished!')
        
        return redirect('journal-detail', pk=entry.pk)


class JournalEntryCreateView(LoginRequiredMixin, CreateView):
    model = JournalEntry
    fields = ['title', 'content', 'tags']
    template_name = 'journal/journalentry_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New Journal Entry'
        context['is_update'] = False
        context['existing_tags'] = []
        context['available_tags'] = Tag.objects.filter(user=self.request.user)
        return context
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        
        # Handle tags
        tags_ids = self.request.POST.getlist('tags')
        
        response = super().form_valid(form)
        
        # Add selected tags
        for tag_id in tags_ids:
            try:
                tag = Tag.objects.get(id=tag_id, user=self.request.user)
                self.object.tags.add(tag)
            except Tag.DoesNotExist:
                pass
        
        messages.success(self.request, f'Your journal entry has been created!')
        return response


class JournalEntryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = JournalEntry
    fields = ['title', 'content', 'tags']
    template_name = 'journal/journalentry_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update Journal Entry'
        context['is_update'] = True
        
        # Get existing tags for this entry
        entry = self.get_object()
        context['existing_tags'] = [tag.id for tag in entry.tags.all()]
        
        # Get all available tags for the user
        context['available_tags'] = Tag.objects.filter(user=self.request.user)
        
        return context
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        
        # Handle tags
        tags_ids = self.request.POST.getlist('tags')
        
        response = super().form_valid(form)
        
        # Clear existing tags and add selected ones
        self.object.tags.clear()
        for tag_id in tags_ids:
            try:
                tag = Tag.objects.get(id=tag_id, user=self.request.user)
                self.object.tags.add(tag)
            except Tag.DoesNotExist:
                pass
        
        messages.success(self.request, f'Your journal entry has been updated!')
        return response
    
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
def preview_polished_entry(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, author=request.user)
    
    if request.method == 'POST':
        try:
            # Get the polished content from the AI
            polish_data = polish_text(entry.content)
            
            # Save the polish data to a JSON file for reference
            json_path = save_polish_data_to_json(entry.id, polish_data)
            
            # Extract the data we need
            polished_content = polish_data.get('polished_text', '')
            evaluation = polish_data.get('evaluation', '')
            topic = polish_data.get('topic', 'General')
            diff_html = polish_data.get('diff_html', '')
            metrics_data = polish_data.get('metrics', {})
            
            # Render the preview template
            context = {
                'entry': entry,
                'polished_content': polished_content,
                'evaluation': evaluation,
                'topic': topic,
                'diff_html': diff_html,
                'metrics_data': metrics_data,
                'json_path': json_path
            }
            
            return render(request, 'journal/preview_polish.html', context)
            
        except Exception as e:
            logger.error(f"Error polishing entry: {str(e)}")
            messages.error(request, f"Error polishing entry: {str(e)}")
            return redirect('journal-detail', pk=pk)
    
    return redirect('journal-detail', pk=pk)


class MyPolishedJournalView(LoginRequiredMixin, ListView):
    model = JournalEntry
    template_name = 'journal/my_polished_journal.html'
    context_object_name = 'polished_entries'

    def get_queryset(self):
        return JournalEntry.objects.filter(author=self.request.user, is_polished=True).order_by('-date_posted')


def polish_entry(request, entry_id):
    entry = get_object_or_404(JournalEntry, id=entry_id)
    if request.method == 'POST':
        polished_content, topic, evaluation, diff_html, metrics = polish_text(
            entry.content)

        # Truncate topic if it's too long
        if topic and len(topic) > 250:
            topic = topic[:250] + "..."

        entry.polished_content = polished_content
        entry.topic = topic
        entry.evaluation = evaluation
        entry.diff_html = diff_html
        entry.metrics_data = metrics
        entry.is_polished = True
        entry.save()
        return redirect('my-polished-journal')
    return render(request, 'journal/journalentry_detail.html', {'object': entry})


def my_polished_journal(request):
    polished_entries = JournalEntry.objects.filter(
        polished_content__isnull=False)
    # Log the polished entries
    logger.debug(f"Polished Entries: {polished_entries}")
    return render(request, 'journal/my_polished_journal.html', {'polished_entries': polished_entries})


@login_required
def download_markdown(request, pk):
    """View to download the markdown file for a journal entry."""
    entry = get_object_or_404(JournalEntry, pk=pk, author=request.user)

    if not entry.markdown_path or not os.path.exists(entry.markdown_path):
        # If markdown doesn't exist, create it
        entry.save_as_markdown()

    if entry.markdown_path and os.path.exists(entry.markdown_path):
        return FileResponse(
            open(entry.markdown_path, 'rb'),
            as_attachment=True,
            filename=os.path.basename(entry.markdown_path)
        )

    messages.error(request, "Markdown file not found.")
    return redirect('journal-detail', pk=entry.pk)


@login_required
def load_from_markdown(request, pk):
    """View to load a journal entry from its markdown file."""
    entry = get_object_or_404(JournalEntry, pk=pk, author=request.user)

    if request.method == 'POST':
        if entry.load_from_markdown():
            entry.save()
            messages.success(
                request, "Entry loaded from markdown file successfully.")
        else:
            messages.error(request, "Failed to load from markdown file.")

    return redirect('journal-detail', pk=entry.pk)


@login_required
def markdown_files_list(request):
    """View to list all markdown files for the user's entries."""
    from journal.markdown_utils import get_markdown_directory
    import os
    import glob
    
    md_dir = get_markdown_directory()
    markdown_files = []
    
    if os.path.exists(md_dir):
        # Get all markdown files
        file_paths = glob.glob(os.path.join(md_dir, '*.md'))
        
        # Get user's entries with markdown paths
        user_entries = JournalEntry.objects.filter(
            author=request.user, 
            markdown_path__isnull=False
        )
        user_paths = set(entry.markdown_path for entry in user_entries)
        
        # Process each file
        for file_path in file_paths:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path) / 1024  # Size in KB
            modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            # Check if this file is associated with one of the user's entries
            is_user_file = file_path in user_paths
            
            if is_user_file:
                markdown_files.append({
                    'name': file_name,
                    'path': file_path,
                    'size': f"{file_size:.1f} KB",
                    'modified': modified_time,
                })
    
    return render(request, 'journal/markdown_files.html', {
        'markdown_files': markdown_files
    })


@login_required
def download_markdown_file(request):
    """View to download a markdown file by path."""
    file_path = request.GET.get('path')
    
    if not file_path or not os.path.exists(file_path):
        messages.error(request, "Markdown file not found.")
        return redirect('markdown-files')
    
    # Security check: make sure the file is in the markdown directory
    from journal.markdown_utils import get_markdown_directory
    md_dir = get_markdown_directory()
    if not file_path.startswith(md_dir):
        messages.error(request, "Invalid file path.")
        return redirect('markdown-files')
    
    # Check if this file belongs to the user
    try:
        entry = JournalEntry.objects.get(markdown_path=file_path, author=request.user)
    except JournalEntry.DoesNotExist:
        messages.error(request, "You don't have permission to download this file.")
        return redirect('markdown-files')
    
    return FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=os.path.basename(file_path)
    )


@login_required
def restore_from_json(request, pk):
    """View to restore polish data from a JSON file."""
    entry = get_object_or_404(JournalEntry, pk=pk, author=request.user)
    
    if request.method == 'POST':
        try:
            # Get the latest polish data
            polish_data = get_latest_polish_data(entry.id)
            
            if polish_data:
                # Update the entry with comprehensive data
                entry.polished_content = polish_data.get('polished_content', '')
                entry.topic = polish_data.get('topic', '')
                
                # Handle evaluation which might be in the new format (object) or old format (string)
                evaluation = polish_data.get('evaluation', '')
                if isinstance(evaluation, dict):
                    entry.evaluation = evaluation.get('full_text', '')
                else:
                    entry.evaluation = evaluation
                
                entry.diff_html = polish_data.get('diff_html', '')
                
                # Handle metrics which might be in the new format (nested) or old format (flat)
                metrics = polish_data.get('metrics', {})
                if isinstance(metrics, dict) and any(k in metrics for k in ['text_statistics', 'quality_metrics', 'change_analysis']):
                    # New format - combine all metrics into a flat structure for backward compatibility
                    combined_metrics = {}
                    for section in ['text_statistics', 'quality_metrics', 'change_analysis']:
                        if section in metrics:
                            combined_metrics.update(metrics[section])
                    entry.metrics_data = combined_metrics
                else:
                    # Old format
                    entry.metrics_data = metrics
                
                entry.is_polished = True
                entry.save()
                
                # Save as markdown
                entry.save_as_markdown()
                
                messages.success(request, 'Polish data restored from JSON backup!')
            else:
                messages.error(request, 'No JSON backup found for this entry.')
                
        except Exception as e:
            logger.error(f"Error in restore_from_json: {e}")
            messages.error(request, f'An error occurred: {str(e)}')
    
    return redirect('journal-detail', pk=entry.pk)


@login_required
def view_comprehensive_polish_data(request, pk):
    """View to display comprehensive polish data."""
    entry = get_object_or_404(JournalEntry, pk=pk, author=request.user)
    
    # Get the latest polish data
    polish_data = get_latest_polish_data(entry.id)
    
    if not polish_data:
        messages.error(request, "No polish data found for this entry.")
        return redirect('journal-detail', pk=entry.pk)
    
    # Prepare context
    context = {
        'entry': entry,
        'polished_content': polish_data.get('polished_content', ''),
        'topic': polish_data.get('topic', ''),
        'diff_html': polish_data.get('diff_html', ''),
        'metrics': polish_data.get('metrics', {}),
    }
    
    # Handle evaluation which might be in the new format (object) or old format (string)
    evaluation = polish_data.get('evaluation', '')
    if isinstance(evaluation, dict):
        context['evaluation'] = evaluation
    else:
        context['evaluation'] = {'full_text': evaluation}
    
    return render(request, 'journal/comprehensive_polish_data.html', context)


@login_required
def download_json(request, pk):
    """View to download the JSON data for a journal entry."""
    entry = get_object_or_404(JournalEntry, pk=pk, author=request.user)
    
    # Get the latest polish data file path
    json_dir = os.path.join(settings.MEDIA_ROOT, 'polish_data')
    if not os.path.exists(json_dir):
        messages.error(request, "JSON directory not found.")
        return redirect('journal-detail', pk=entry.pk)
    
    # Find all JSON files for this entry
    files = [f for f in os.listdir(json_dir) if f.startswith(f"{entry.id}_") and f.endswith('.json')]
    
    if not files:
        messages.error(request, "No JSON files found for this entry.")
        return redirect('journal-detail', pk=entry.pk)
    
    # Sort by timestamp (which is part of the filename)
    files.sort(reverse=True)
    
    # Get the latest file
    latest_file = os.path.join(json_dir, files[0])
    
    return FileResponse(
        open(latest_file, 'rb'),
        as_attachment=True,
        filename=os.path.basename(latest_file)
    )


@login_required
def journal_entry_detail(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, author=request.user)
    
    # Get recent entries for the sidebar
    recent_entries = JournalEntry.objects.filter(
        author=request.user
    ).exclude(
        id=entry.id
    ).order_by('-date_posted')[:5]
    
    # Get current month for stats
    current_month = datetime.now().month
    
    # Calculate stats
    total_entries = JournalEntry.objects.filter(author=request.user).count()
    polished_entries = JournalEntry.objects.filter(author=request.user, is_polished=True).count()
    monthly_entries = JournalEntry.objects.filter(
        author=request.user,
        date_posted__month=current_month
    ).count()
    
    context = {
        'object': entry,
        'recent_entries': recent_entries,
        'total_entries': total_entries,
        'polished_entries': polished_entries,
        'monthly_entries': monthly_entries,
    }
    
    return render(request, 'journal/journalentry_detail.html', context)


@login_required
def analytics_view(request):
    # Get all entries for the user
    entries = JournalEntry.objects.filter(author=request.user)
    
    # Basic stats
    total_entries = entries.count()
    polished_entries = entries.filter(is_polished=True).count()
    
    # Calculate average words - using Python instead of PostgreSQL functions
    total_words = 0
    for entry in entries:
        total_words += len(entry.content.split())
    
    avg_words = round(total_words / max(total_entries, 1))
    
    # Calculate streak
    dates = list(entries.values_list('date_posted', flat=True).order_by('date_posted'))
    streak = calculate_streak(dates)
    
    # Entry activity over time
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    activity_data = {}
    current_date = start_date
    while current_date <= end_date:
        activity_data[current_date.strftime('%Y-%m-%d')] = 0
        current_date += timedelta(days=1)
    
    for entry in entries.filter(date_posted__gte=start_date):
        date_str = entry.date_posted.strftime('%Y-%m-%d')
        if date_str in activity_data:
            activity_data[date_str] += 1
    
    activity_dates = list(activity_data.keys())
    activity_counts = list(activity_data.values())
    
    # Top tags
    from django.db.models import Count
    tags = Tag.objects.filter(journalentry__author=request.user).annotate(
        entry_count=Count('journalentry')
    ).order_by('-entry_count')[:5]
    
    tag_names = [tag.name for tag in tags]
    tag_counts = [tag.entry_count for tag in tags]
    
    # Topic distribution
    topics = entries.filter(is_polished=True).values('topic').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    topic_names = [topic['topic'] for topic in topics]
    topic_counts = [topic['count'] for topic in topics]
    
    context = {
        'total_entries': total_entries,
        'polished_entries': polished_entries,
        'avg_words': avg_words,
        'streak': streak,
        'activity_dates': json.dumps(activity_dates),
        'activity_counts': json.dumps(activity_counts),
        'tag_names': json.dumps(tag_names),
        'tag_counts': json.dumps(tag_counts),
        'topic_names': json.dumps(topic_names),
        'topic_counts': json.dumps(topic_counts),
    }
    
    return render(request, 'journal/analytics.html', context)

def calculate_streak(dates):
    if not dates:
        return 0
    
    from datetime import datetime, timedelta
    today = datetime.now().date()
    
    # Convert all dates to date objects if they aren't already
    dates = [d.date() if hasattr(d, 'date') else d for d in dates]
    
    # Get unique dates and sort them
    unique_dates = sorted(set(dates))
    
    # Check if there's an entry today
    if today not in unique_dates:
        # If no entry today, start counting from yesterday
        current_date = today - timedelta(days=1)
    else:
        current_date = today
    
    streak = 0
    while current_date in unique_dates:
        streak += 1
        current_date -= timedelta(days=1)
    
    return streak

@login_required
def export_to_pdf(request, pk=None):
    if pk:
        # Export single entry
        entry = get_object_or_404(JournalEntry, pk=pk, author=request.user)
        entries = [entry]
        filename = f"journal_entry_{entry.id}.pdf"
    else:
        # Export all entries or filtered entries
        entries = JournalEntry.objects.filter(author=request.user).order_by('-date_posted')
        
        # Apply filters if any
        search_query = request.GET.get('search')
        if search_query:
            entries = entries.filter(
                Q(title__icontains=search_query) | 
                Q(content__icontains=search_query)
            )
        
        tag_id = request.GET.get('tag')
        if tag_id:
            entries = entries.filter(tags__id=tag_id)
        
        polished = request.GET.get('polished')
        if polished == '1':
            entries = entries.filter(is_polished=True)
        elif polished == '0':
            entries = entries.filter(is_polished=False)
        
        date_from = request.GET.get('date_from')
        if date_from:
            entries = entries.filter(date_posted__gte=date_from)
        
        date_to = request.GET.get('date_to')
        if date_to:
            entries = entries.filter(date_posted__lte=date_to)
        
        filename = "journal_entries.pdf"
    
    # Render PDF
    context = {
        'entries': entries,
        'user': request.user,
        'date': datetime.now(),
    }
    
    pdf = render_to_pdf('journal/pdf_template.html', context)
    
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    return HttpResponse("Error generating PDF", status=400)

@login_required
def create_tags(request):
    if request.method == 'POST':
        # Check if it's an AJAX request by examining headers
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if is_ajax:
            tags_str = request.POST.get('tags', '')
            tag_names = [name.strip() for name in tags_str.split(',') if name.strip()]
            
            created_tags = []
            for name in tag_names:
                tag, created = Tag.objects.get_or_create(name=name, user=request.user)
                created_tags.append({
                    'id': tag.id,
                    'name': tag.name
                })
            
            return JsonResponse({'tags': created_tags})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)
