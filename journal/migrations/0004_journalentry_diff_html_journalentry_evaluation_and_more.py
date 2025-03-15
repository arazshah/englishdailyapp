# Generated by Django 4.2.7 on 2025-03-15 13:33

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("journal", "0003_alter_journalentry_date_posted_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="journalentry",
            name="diff_html",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="journalentry",
            name="evaluation",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="journalentry",
            name="metrics_data",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="journalentry",
            name="topic",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="journalentry",
            name="date_posted",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
